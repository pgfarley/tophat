# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.host.tophat_host import (  # noqa: E402
    FEATURE_VECTOR_BYTES,
    MODEL_IMAGE_BYTES,
    TophatClient,
)


class _FakeTransport:
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    def request(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(payload)
        if not self.responses:
            raise AssertionError("No fake response queued")
        return self.responses.pop(0)


def test_load_model_sends_expected_payload() -> None:
    fake = _FakeTransport([{"ok": True}])
    client = TophatClient(fake)

    model = bytes(range(MODEL_IMAGE_BYTES))
    client.load_model(model)

    assert fake.requests == [{"cmd": "load_model", "model": list(model)}]


def test_predict_sends_features_and_returns_prediction() -> None:
    fake = _FakeTransport([{"ok": True, "prediction": 123}])
    client = TophatClient(fake)

    features = list(range(FEATURE_VECTOR_BYTES))
    pred = client.predict(features)

    assert pred == 123
    assert fake.requests == [{"cmd": "predict", "features": features}]


def test_load_model_rejects_wrong_length() -> None:
    fake = _FakeTransport([{"ok": True}])
    client = TophatClient(fake)

    with pytest.raises(ValueError, match="exactly 46"):
        client.load_model(bytes([0] * (MODEL_IMAGE_BYTES - 1)))


def test_run_rejects_missing_prediction() -> None:
    fake = _FakeTransport([{"ok": True}])
    client = TophatClient(fake)

    with pytest.raises(RuntimeError, match="invalid `prediction`"):
        client.run()


def test_request_raises_board_error() -> None:
    fake = _FakeTransport([{"ok": False, "error": "missing model"}])
    client = TophatClient(fake)

    with pytest.raises(RuntimeError, match="missing model"):
        client.clear()
