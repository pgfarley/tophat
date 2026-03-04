# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.host.tophat_host import JsonLineSerialTransport, ProtocolError, _decode_json_object  # noqa: E402


class _FakeSerialPort:
    def __init__(self, responses: list[bytes]):
        self._responses = responses
        self.writes: list[bytes] = []
        self.reset_calls = 0

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def flush(self) -> None:
        return None

    def readline(self) -> bytes:
        if self._responses:
            return self._responses.pop(0)
        return b""

    def reset_input_buffer(self) -> None:
        self.reset_calls += 1

    def close(self) -> None:
        return None


class _FakeSerialModule:
    def __init__(self, port: _FakeSerialPort):
        self._port = port

    def Serial(self, _port: str, _baud: int, timeout: float) -> _FakeSerialPort:
        assert timeout > 0
        return self._port


def test_decode_json_object_from_mixed_line() -> None:
    raw = b'T: ^[[32;1mDe{"cmd":"ping"}\r\n'
    decoded = _decode_json_object(raw)
    assert decoded == {"cmd": "ping"}


def test_transport_skips_echoed_command_until_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    port = _FakeSerialPort(
        [
            b'T: ^[[32;1mDe{"cmd":"ping"}\r\n',
            b'{"ok":true,"bridge":"tophat-rpc","protocol":1}\n',
        ]
    )
    monkeypatch.setitem(sys.modules, "serial", _FakeSerialModule(port))

    transport = JsonLineSerialTransport("/dev/ttyACM0", timeout_s=0.05)
    response = transport.request({"cmd": "ping"})

    assert response == {"ok": True, "bridge": "tophat-rpc", "protocol": 1}
    assert port.writes == [b'{"cmd":"ping"}\n']
    assert port.reset_calls == 1


def test_transport_times_out_with_only_echo(monkeypatch: pytest.MonkeyPatch) -> None:
    port = _FakeSerialPort([b'{"cmd":"ping"}\n'])
    monkeypatch.setitem(sys.modules, "serial", _FakeSerialModule(port))

    transport = JsonLineSerialTransport("/dev/ttyACM0", timeout_s=0.01)
    with pytest.raises(ProtocolError, match="Missing boolean `ok` in response"):
        transport.request({"cmd": "ping"})
