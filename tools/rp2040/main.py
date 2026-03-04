#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

"""
TOPHAT RP2040 JSON-RPC bridge.

Copy this file to the board as :main.py and reset. The host utility
tools/host/tophat_host.py can then talk to it over USB CDC serial.
"""

try:
    import ujson as json
except ImportError:
    import json

import sys
import time
import builtins

from ttboard.boot.demoboard_detect import DemoboardDetect
from ttboard.demoboard import DemoBoard
from ttboard.mode import RPMode


# Must match info.yaml top module.
PROJECT_NAME = "tt_um_pgfarley_tophat_top"

MODEL_IMAGE_BYTES = 22
FEATURE_VECTOR_BYTES = 8

CMD_MODEL = 0b00
CMD_FEATURE = 0b01
CMD_CTRL = 0b10

CTRL_RUN = 0x01
CTRL_CLEAR = 0x02

PROTOCOL_VERSION = 1
BOOT_LOG_PATH = "tophat_boot.log"


def _ticks_deadline(timeout_ms):
    return time.ticks_add(time.ticks_ms(), timeout_ms)


def _before_deadline(deadline):
    return time.ticks_diff(deadline, time.ticks_ms()) > 0


def _send_response(obj):
    try:
        out = sys.stdout
    except Exception:
        return

    try:
        out.write(json.dumps(obj))
        out.write("\n")
        if hasattr(out, "flush"):
            out.flush()
    except Exception:
        # Serial may disappear during USB reconnect; keep main loop alive.
        return


def _ok(**fields):
    payload = {"ok": True}
    payload.update(fields)
    _send_response(payload)


def _err(message):
    _send_response({"ok": False, "error": str(message)})


def _validate_u8_list(values, expected_len, label):
    if not isinstance(values, list):
        raise ValueError("%s must be a list of %d bytes" % (label, expected_len))
    if len(values) != expected_len:
        raise ValueError("%s must contain exactly %d bytes (got %d)" % (label, expected_len, len(values)))

    out = []
    idx = 0
    for value in values:
        if not isinstance(value, int):
            raise ValueError("%s[%d] must be an int (got %r)" % (label, idx, value))
        if value < 0 or value > 0xFF:
            raise ValueError("%s[%d] must be in 0..255 (got %r)" % (label, idx, value))
        out.append(value)
        idx += 1
    return out


class TophatBridge:
    def __init__(self):
        self.tt = None
        self._ready = False
        self._init_error = ""
        self._project_enabled = ""
        try:
            DemoboardDetect.probe()
            self.tt = DemoBoard.get()
            self._setup_board()
            self._ready = True
        except Exception as exc:
            self._init_error = str(exc)

    def _setup_board(self):
        # Drive inputs/control from RP side for command protocol.
        if self.tt.mode != RPMode.ASIC_RP_CONTROL:
            self.tt.mode = RPMode.ASIC_RP_CONTROL

        # ASIC drives uio[7:3], RP2040 drives uio[2:0] (valid + cmd).
        self.tt.uio_oe_pico.value = 0x07
        self.tt.ui_in.value = 0
        self.tt.uio_in.value = 0

        enabled = getattr(self.tt.shuttle, "enabled", None)
        self._project_enabled = str(enabled) if enabled is not None else ""
        self._pulse_reset()

    def _pulse_reset(self):
        # Use the default TT firmware reset path.
        self.tt.reset_project(True)
        time.sleep_ms(1)
        self.tt.reset_project(False)

    def ready(self):
        return self._ready

    def init_error(self):
        return self._init_error

    def project_enabled(self):
        return self._project_enabled

    def mode(self):
        try:
            return self.tt.mode_str
        except Exception:
            return "UNKNOWN"

    def _require_ready(self):
        if not self._ready:
            raise RuntimeError("Bridge not ready: %s" % self._init_error)

    def _tick(self):
        if hasattr(self.tt, "clock_project_once"):
            self.tt.clock_project_once()
            return

        if hasattr(self.tt, "clk"):
            self.tt.clk.value = 1
            time.sleep_us(2)
            self.tt.clk.value = 0
            time.sleep_us(2)
            return

        raise RuntimeError("No project clock method available (expected clock_project_once or clk pin)")

    def _reset(self):
        self.tt.rst_n.value = 0
        for _ in range(10):
            self._tick()
        self.tt.rst_n.value = 1
        for _ in range(2):
            self._tick()

    def _status(self):
        raw = int(self.tt.uio_out.value)
        return {
            "ready": (raw >> 3) & 0x1,
            "busy": (raw >> 4) & 0x1,
            "pred_valid": (raw >> 5) & 0x1,
            "model_loaded": (raw >> 6) & 0x1,
            "error_or_missing_features": (raw >> 7) & 0x1,
        }

    def _wait_until(self, predicate, timeout_ms, label):
        deadline = _ticks_deadline(timeout_ms)
        while _before_deadline(deadline):
            if predicate():
                return
            self._tick()
        raise RuntimeError("Timeout waiting for %s" % label)

    def _send_cmd_byte(self, cmd, payload):
        self._wait_until(lambda: self._status()["ready"] == 1, 150, "ready")

        self.tt.ui_in.value = payload & 0xFF
        self.tt.uio_in.value = ((cmd & 0x3) << 1) | 0x1
        self._tick()

        self.tt.uio_in.value = 0
        self.tt.ui_in.value = 0
        self._tick()

    def clear(self):
        self._require_ready()
        self._send_cmd_byte(CMD_CTRL, CTRL_CLEAR)

    def load_model(self, model):
        self._require_ready()
        for byte in model:
            self._send_cmd_byte(CMD_MODEL, byte)

        self._wait_until(lambda: self._status()["model_loaded"] == 1, 250, "model_loaded")

    def load_features(self, features):
        self._require_ready()
        for byte in features:
            self._send_cmd_byte(CMD_FEATURE, byte)

    def run(self):
        self._require_ready()
        self._send_cmd_byte(CMD_CTRL, CTRL_RUN)

        deadline = _ticks_deadline(300)
        while _before_deadline(deadline):
            status = self._status()
            if status["pred_valid"] == 1:
                return int(self.tt.uo_out.value) & 0xFF
            if status["busy"] == 0 and status["error_or_missing_features"] == 1:
                raise RuntimeError("Run rejected (missing model/features or core error)")
            self._tick()

        raise RuntimeError("Timeout waiting for prediction")

    def predict(self, features):
        self.load_features(features)
        return self.run()


def _handle_request(bridge, req):
    if not isinstance(req, dict):
        raise ValueError("Request must be a JSON object")

    cmd = req.get("cmd")
    if not isinstance(cmd, str):
        raise ValueError("Missing string `cmd`")

    if cmd == "ping":
        payload = {
            "ok": True,
            "protocol_version": PROTOCOL_VERSION,
            "project_enabled": bridge.project_enabled(),
            "mode": bridge.mode(),
        }
        if not bridge.ready():
            payload["init_error"] = bridge.init_error()
        return payload

    if cmd == "clear":
        bridge.clear()
        return {"ok": True}

    if cmd == "load_model":
        model = _validate_u8_list(req.get("model"), MODEL_IMAGE_BYTES, "model")
        bridge.load_model(model)
        return {"ok": True}

    if cmd == "load_features":
        features = _validate_u8_list(req.get("features"), FEATURE_VECTOR_BYTES, "features")
        bridge.load_features(features)
        return {"ok": True}

    if cmd == "run":
        prediction = bridge.run()
        return {"ok": True, "prediction": prediction}

    if cmd == "predict":
        features = _validate_u8_list(req.get("features"), FEATURE_VECTOR_BYTES, "features")
        prediction = bridge.predict(features)
        return {"ok": True, "prediction": prediction}

    return {"ok": False, "error": "Unsupported command: %s" % cmd}


def _boot_bridge_with_log():
    boot_log = None
    original_print = builtins.print
    print_redirected = False

    try:
        boot_log = open(BOOT_LOG_PATH, "a")
        try:
            original_print("=== boot ===", file=boot_log)
            boot_log.flush()
        except Exception:
            pass

        def _boot_print(*args, **kwargs):
            # Redirect default console prints to log while preserving explicit file= targets.
            if kwargs.get("file") is None:
                kwargs = dict(kwargs)
                kwargs["file"] = boot_log
            return original_print(*args, **kwargs)

        builtins.print = _boot_print
        print_redirected = True
    except Exception:
        boot_log = None

    try:
        return TophatBridge()
    finally:
        if print_redirected:
            try:
                builtins.print = original_print
            except Exception:
                pass
        if boot_log is not None:
            try:
                boot_log.flush()
            except Exception:
                pass
            try:
                boot_log.close()
            except Exception:
                pass


def main():
    bridge = _boot_bridge_with_log()

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                time.sleep_ms(10)
                continue

            line = line.strip()
            if not line:
                continue

            try:
                req = json.loads(line)
            except Exception:
                # Ignore serial noise so host RPC stays request/response aligned.
                continue

            try:
                resp = _handle_request(bridge, req)
            except Exception as exc:
                _err(exc)
                continue

            _send_response(resp)

        except Exception:
            # Common when USB CDC disconnects/reconnects while reading stdin.
            time.sleep_ms(20)


if __name__ == "__main__":
    main()
