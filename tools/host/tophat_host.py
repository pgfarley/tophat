#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Protocol

MODEL_IMAGE_BYTES = 22
FEATURE_VECTOR_BYTES = 8


class ProtocolError(RuntimeError):
    """Raised when the RPC payload shape is invalid."""


class RequestTransport(Protocol):
    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send one request and return one response."""


class JsonLineSerialTransport:
    """Line-delimited JSON transport over USB serial (CDC)."""

    def __init__(self, port: str, baud: int = 115200, timeout_s: float = 2.0):
        self._port = port
        self._baud = baud
        self._timeout_s = timeout_s
        self._serial: Any | None = None

    def __enter__(self) -> "JsonLineSerialTransport":
        self._open()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _open(self) -> None:
        if self._serial is not None:
            return
        try:
            import serial  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised only when pyserial is missing
            raise RuntimeError(
                "pyserial is required for serial transport; install with `pip install pyserial`"
            ) from exc

        self._serial = serial.Serial(self._port, self._baud, timeout=self._timeout_s)

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._open()
        assert self._serial is not None

        line = json.dumps(payload, separators=(",", ":")) + "\n"
        self._serial.write(line.encode("utf-8"))
        self._serial.flush()

        response_raw = self._serial.readline()
        if not response_raw:
            raise TimeoutError("Timeout waiting for board response")

        try:
            response = json.loads(response_raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ProtocolError(f"Invalid JSON response: {response_raw!r}") from exc

        if not isinstance(response, dict):
            raise ProtocolError(f"Expected object response, got: {response!r}")
        return response


class TophatClient:
    def __init__(self, transport: RequestTransport):
        self._transport = transport

    def ping(self) -> dict[str, Any]:
        return self._request("ping")

    def clear(self) -> None:
        self._request("clear")

    def load_model(self, model_bytes: bytes | Iterable[int]) -> None:
        model = _normalize_u8_vector(model_bytes, MODEL_IMAGE_BYTES, label="model")
        self._request("load_model", model=model)

    def load_features(self, feature_values: Iterable[int]) -> None:
        features = _normalize_u8_vector(feature_values, FEATURE_VECTOR_BYTES, label="features")
        self._request("load_features", features=features)

    def run(self) -> int:
        response = self._request("run")
        return _read_prediction(response)

    def predict(self, feature_values: Iterable[int]) -> int:
        features = _normalize_u8_vector(feature_values, FEATURE_VECTOR_BYTES, label="features")
        response = self._request("predict", features=features)
        return _read_prediction(response)

    def _request(self, cmd: str, **fields: Any) -> dict[str, Any]:
        payload = {"cmd": cmd}
        payload.update(fields)
        response = self._transport.request(payload)

        ok = response.get("ok")
        if not isinstance(ok, bool):
            raise ProtocolError(f"Missing boolean `ok` in response: {response!r}")
        if not ok:
            error = response.get("error", "unknown error")
            raise RuntimeError(f"Board error: {error}")
        return response


def _normalize_u8_vector(
    values: bytes | Iterable[int], expected_len: int, label: str
) -> list[int]:
    if isinstance(values, (bytes, bytearray)):
        out = list(values)
    else:
        out = [int(v) for v in values]

    if len(out) != expected_len:
        raise ValueError(f"{label} must contain exactly {expected_len} bytes (got {len(out)})")

    for idx, value in enumerate(out):
        if not (0 <= value <= 0xFF):
            raise ValueError(f"{label}[{idx}] must be in 0..255 (got {value})")
    return out


def _read_prediction(response: dict[str, Any]) -> int:
    prediction = response.get("prediction")
    if not isinstance(prediction, int) or not (0 <= prediction <= 0xFF):
        raise ProtocolError(f"Missing or invalid `prediction` byte in response: {response!r}")
    return prediction


def _parse_feature_csv(csv_values: str) -> list[int]:
    parts = [p.strip() for p in csv_values.split(",") if p.strip() != ""]
    return _normalize_u8_vector([int(p, 0) for p in parts], FEATURE_VECTOR_BYTES, label="features")


def _load_feature_file(path: Path) -> list[int]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return _normalize_u8_vector(data, FEATURE_VECTOR_BYTES, label="features")
    if isinstance(data, dict):
        ordered = [int(data.get(f"feature_{idx:02d}", 0)) for idx in range(FEATURE_VECTOR_BYTES)]
        return _normalize_u8_vector(ordered, FEATURE_VECTOR_BYTES, label="features")
    raise ValueError("Feature JSON must be either a list[8] or an object with feature_00..feature_07 keys")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Host utility for TOPHAT USB-serial RPC bridge")

    subparsers = parser.add_subparsers(dest="subcmd", required=True)
    ping = subparsers.add_parser("ping", help="Check bridge liveness")
    _add_transport_args(ping)
    clear = subparsers.add_parser("clear", help="Clear model/features/core state")
    _add_transport_args(clear)

    load_model = subparsers.add_parser("load-model", help="Load 22-byte model image")
    _add_transport_args(load_model)
    load_model.add_argument("--model", required=True, help="Path to 22-byte model binary")

    load_features = subparsers.add_parser("load-features", help="Load 8-byte feature vector")
    _add_transport_args(load_features)
    _add_feature_args(load_features)

    run = subparsers.add_parser("run", help="Run predict after features are already loaded")
    _add_transport_args(run)

    predict = subparsers.add_parser("predict", help="Load features then run predict")
    _add_transport_args(predict)
    _add_feature_args(predict)
    return parser


def _add_transport_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port", required=True, help="Serial port, e.g. /dev/ttyACM0")


def _add_feature_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--features",
        help="Comma-separated 8-byte vector, e.g. 4,6,10,12,15,20,10,18",
    )
    group.add_argument("--features-file", help="JSON file containing list[8] or feature_00..feature_07 object")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    with JsonLineSerialTransport(args.port) as transport:
        client = TophatClient(transport)

        if args.subcmd == "ping":
            response = client.ping()
            print(json.dumps(response, sort_keys=True))
            return 0

        if args.subcmd == "clear":
            client.clear()
            print(json.dumps({"ok": True, "cmd": "clear"}))
            return 0

        if args.subcmd == "load-model":
            model = Path(args.model).read_bytes()
            client.load_model(model)
            print(json.dumps({"ok": True, "cmd": "load-model", "bytes": len(model)}))
            return 0

        if args.subcmd in ("load-features", "predict"):
            if args.features is not None:
                features = _parse_feature_csv(args.features)
            else:
                features = _load_feature_file(Path(args.features_file))

            if args.subcmd == "load-features":
                client.load_features(features)
                print(json.dumps({"ok": True, "cmd": "load-features", "bytes": len(features)}))
                return 0

            prediction = client.predict(features)
            print(json.dumps({"ok": True, "cmd": "predict", "prediction": prediction}))
            return 0

        if args.subcmd == "run":
            prediction = client.run()
            print(json.dumps({"ok": True, "cmd": "run", "prediction": prediction}))
            return 0

    raise RuntimeError(f"Unsupported subcommand: {args.subcmd}")


if __name__ == "__main__":
    raise SystemExit(main())
