# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
import joblib

from fixture_data import EXAMPLES, vectorize, vectorize_u8
from generate_golden_tree import write_artifacts

CMD_MODEL = 0b00
CMD_FEATURE = 0b01
CMD_CTRL = 0b10


def _status(dut: cocotb.handle.SimHandleBase) -> dict[str, int]:
    raw = int(dut.uio_out.value)
    return {
        "ready": (raw >> 3) & 0x1,
        "busy": (raw >> 4) & 0x1,
        "pred_valid": (raw >> 5) & 0x1,
        "model_loaded": (raw >> 6) & 0x1,
        "error_or_missing_features": (raw >> 7) & 0x1,
    }


async def _wait_until(dut: cocotb.handle.SimHandleBase, predicate, timeout_cycles: int, label: str) -> None:
    for _ in range(timeout_cycles):
        if predicate():
            return
        await ClockCycles(dut.clk, 1)
    raise AssertionError(f"Timeout waiting for {label}")


async def _send_cmd_byte(dut: cocotb.handle.SimHandleBase, cmd: int, payload: int) -> None:
    dut.ui_in.value = payload & 0xFF
    dut.uio_in.value = ((cmd & 0x3) << 1) | 0x1
    await ClockCycles(dut.clk, 1)
    dut.uio_in.value = 0
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 1)


async def _clear(dut: cocotb.handle.SimHandleBase) -> None:
    await _wait_until(dut, lambda: _status(dut)["ready"] == 1, 50, "ready before clear")
    await _send_cmd_byte(dut, CMD_CTRL, 0x02)


async def _load_model(dut: cocotb.handle.SimHandleBase, model_image: bytes) -> None:
    for byte in model_image:
        await _wait_until(dut, lambda: _status(dut)["ready"] == 1, 50, "ready during model load")
        await _send_cmd_byte(dut, CMD_MODEL, byte)
    await _wait_until(
        dut,
        lambda: _status(dut)["model_loaded"] == 1,
        50,
        "model_loaded status",
    )


async def _load_features(dut: cocotb.handle.SimHandleBase, feature_values: list[int]) -> None:
    assert len(feature_values) == 8
    for value in feature_values:
        await _wait_until(dut, lambda: _status(dut)["ready"] == 1, 50, "ready during feature load")
        await _send_cmd_byte(dut, CMD_FEATURE, value)


async def _run_predict(dut: cocotb.handle.SimHandleBase) -> int:
    await _wait_until(dut, lambda: _status(dut)["ready"] == 1, 50, "ready before run")
    await _send_cmd_byte(dut, CMD_CTRL, 0x01)

    await _wait_until(
        dut,
        lambda: _status(dut)["pred_valid"] == 1,
        50,
        "pred_valid status",
    )
    return int(dut.uo_out.value) & 0xFF


async def _reset(dut: cocotb.handle.SimHandleBase) -> None:
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_model_load_and_predict(dut: cocotb.handle.SimHandleBase) -> None:
    clock = Clock(dut.clk, 10, unit="us")
    cocotb.start_soon(clock.start())
    await _reset(dut)

    test_dir = Path(__file__).resolve().parent
    tree_path = test_dir / "golden_tree.joblib"
    model_path = test_dir / "golden_model.bin"

    if not tree_path.exists() or not model_path.exists():
        write_artifacts(test_dir)

    clf = joblib.load(tree_path)
    model_image = model_path.read_bytes()
    assert len(model_image) == 36, f"Expected 36-byte model image, got {len(model_image)}"

    await _clear(dut)
    await _load_model(dut, model_image)

    for case in EXAMPLES:
        features_u8 = vectorize_u8(case["features"])
        await _load_features(dut, features_u8)
        dut_pred = await _run_predict(dut)

        x = vectorize(case["features"]).reshape(1, -1)
        golden_pred = int(round(float(clf.predict(x)[0])))

        assert golden_pred == case["expected"], (
            f"{case['name']}: fixture expected {case['expected']}, golden model predicted {golden_pred}"
        )
        assert dut_pred == golden_pred, (
            f"{case['name']}: DUT predicted {dut_pred}, golden model predicted {golden_pred}"
        )

