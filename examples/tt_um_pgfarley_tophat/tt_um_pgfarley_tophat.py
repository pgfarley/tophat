# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

import microcotb as cocotb
from microcotb.clock import Clock
from microcotb.triggers import ClockCycles
from ttboard.cocotb.dut import DUT
from ttboard.demoboard import DemoBoard
from ttboard.mode import RPMode

from .fixture_data import EXAMPLES, vectorize_u8
from .model_image import MODEL_IMAGE

cocotb.set_runner_scope(__name__)

PROJECT_NAME = "tt_um_pgfarley_tophat"

CMD_MODEL = 0b00
CMD_FEATURE = 0b01
CMD_CTRL = 0b10


def _status(dut):
    raw = int(dut.uio_out.value)
    return {
        "ready": (raw >> 3) & 0x1,
        "busy": (raw >> 4) & 0x1,
        "pred_valid": (raw >> 5) & 0x1,
        "model_loaded": (raw >> 6) & 0x1,
        "error_or_missing_features": (raw >> 7) & 0x1,
    }


async def _wait_until(dut, predicate, timeout_cycles, label):
    for _ in range(timeout_cycles):
        if predicate():
            return
        await ClockCycles(dut.clk, 1)
    raise AssertionError(f"Timeout waiting for {label}")


async def _send_cmd_byte(dut, cmd, payload):
    dut.ui_in.value = payload & 0xFF
    dut.uio_in.value = ((cmd & 0x3) << 1) | 0x1
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1)


async def _clear(dut):
    await _wait_until(dut, lambda: _status(dut)["ready"] == 1, 50, "ready before clear")
    await _send_cmd_byte(dut, CMD_CTRL, 0x02)


async def _load_model(dut, model_image):
    for byte in model_image:
        await _wait_until(dut, lambda: _status(dut)["ready"] == 1, 50, "ready during model load")
        await _send_cmd_byte(dut, CMD_MODEL, byte)
    await _wait_until(dut, lambda: _status(dut)["model_loaded"] == 1, 50, "model_loaded status")


async def _load_features(dut, feature_values):
    assert len(feature_values) == 8
    for value in feature_values:
        await _wait_until(dut, lambda: _status(dut)["ready"] == 1, 50, "ready during feature load")
        await _send_cmd_byte(dut, CMD_FEATURE, value)


async def _run_predict(dut):
    await _wait_until(dut, lambda: _status(dut)["ready"] == 1, 50, "ready before run")
    await _send_cmd_byte(dut, CMD_CTRL, 0x01)
    await _wait_until(dut, lambda: _status(dut)["pred_valid"] == 1, 50, "pred_valid status")
    return int(dut.uo_out.value) & 0xFF


async def _reset(dut):
    dut.ena.value = 1
    # ASIC drives uio[7:3], RP2040 must drive uio[2:0] (valid + cmd).
    dut.uio_oe_pico.value = 0x07
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_model_load_and_predict_fixture_only(dut):
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    await _reset(dut)

    assert len(MODEL_IMAGE) == 36, f"Expected 36-byte model image, got {len(MODEL_IMAGE)}"

    await _clear(dut)
    await _load_model(dut, MODEL_IMAGE)

    for case in EXAMPLES:
        features_u8 = vectorize_u8(case["features"])
        await _load_features(dut, features_u8)
        dut_pred = await _run_predict(dut)

        expected = int(case["expected"])
        assert dut_pred == expected, (
            f"{case['name']}: DUT predicted {dut_pred}, fixture expected {expected}"
        )


def _load_project(tt):
    if not tt.shuttle.has(PROJECT_NAME):
        print(f"This shuttle does not contain {PROJECT_NAME}")
        return False

    getattr(tt.shuttle, PROJECT_NAME).enable()

    if tt.mode != RPMode.ASIC_RP_CONTROL:
        print("Setting mode to ASIC_RP_CONTROL")
        tt.mode = RPMode.ASIC_RP_CONTROL

    tt.uio_oe_pico.value = 0x07
    return True


def main():
    tt = DemoBoard.get()
    if not _load_project(tt):
        return

    dut = DUT()
    runner = cocotb.get_runner(__name__)
    dut._log.info(f"enabled {PROJECT_NAME}, running tests")
    runner.test(dut)
