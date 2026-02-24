#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from fixture_data import EXAMPLES, FEATURES


def test_golden_tree_predictions() -> None:
    model_path = Path(__file__).resolve().parent / "golden_tree.joblib"
    assert model_path.exists(), f"Missing model file: {model_path}"
    clf = joblib.load(model_path)

    for case in EXAMPLES:
        x = np.array([case["features"][name] for name in FEATURES], dtype=np.int64).reshape(1, -1)
        pred = float(clf.predict(x)[0])
        assert pred == case["expected"], (
            f"{case['name']}: expected {case['expected']}, got {pred}"
        )
