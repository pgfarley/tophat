#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import joblib
from fixture_data import EXAMPLES, vectorize


def test_golden_tree_predictions() -> None:
    model_path = Path(__file__).resolve().parent / "golden_tree.joblib"
    assert model_path.exists(), f"Missing model file: {model_path}"
    clf = joblib.load(model_path)

    for case in EXAMPLES:
        x = vectorize(case["features"])
        pred = float(clf.predict(x.reshape(1, -1))[0])
        assert pred == case["expected"], (
            f"{case['name']}: expected {case['expected']}, got {pred}"
        )
