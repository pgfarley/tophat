# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fixture_data import EXAMPLES as TEST_EXAMPLES
from fixture_data import FEATURES as TEST_FEATURES
from examples.tt_um_pgfarley_tophat.fixture_data import EXAMPLES as EXAMPLE_EXAMPLES
from examples.tt_um_pgfarley_tophat.fixture_data import FEATURES as EXAMPLE_FEATURES
from examples.tt_um_pgfarley_tophat.model_image import MODEL_IMAGE


def test_example_fixture_data_matches_local_fixture_data() -> None:
    assert EXAMPLE_FEATURES == TEST_FEATURES
    assert EXAMPLE_EXAMPLES == TEST_EXAMPLES


def test_example_model_image_matches_golden_model_file() -> None:
    golden_model_path = Path(__file__).resolve().parent / "golden_model.bin"
    assert golden_model_path.exists(), f"Missing model file: {golden_model_path}"
    assert MODEL_IMAGE == golden_model_path.read_bytes()
