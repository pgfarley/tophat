#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.tree import DecisionTreeClassifier

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.host.tophat_host import (  # noqa: E402
    FEATURE_VECTOR_BYTES,
    MODEL_IMAGE_BYTES,
    JsonLineSerialTransport,
    TophatClient,
)

COMPETITION = "titanic"
TREE_DEPTH = 3
NUM_INTERNAL = (1 << TREE_DEPTH) - 1
NUM_LEAVES = 1 << TREE_DEPTH

FEATURE_NAMES = [
    "pclass",
    "sex_male",
    "age",
    "sibsp",
    "parch",
    "fare",
    "embarked",
    "is_alone",
]


@dataclass(frozen=True)
class ScaleStats:
    minimum: float
    maximum: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a depth-3/8-feature Titanic model and run Kaggle inference on TOPHAT ASIC.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("../titanic-xgboost/data/raw"),
        help="Directory containing Kaggle train.csv/test.csv (default: ../titanic-xgboost/data/raw).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/titanic_asic_demo"),
        help="Directory for generated model/submission/report artifacts.",
    )
    parser.add_argument(
        "--port",
        help="Serial port for RP2040 bridge (for example /dev/ttyACM0). Required unless --skip-board.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download Kaggle Titanic CSVs with Kaggle CLI into --data-dir before training.",
    )
    parser.add_argument(
        "--skip-board",
        action="store_true",
        help="Skip ASIC inference and emit software-only submission.",
    )
    parser.add_argument(
        "--submit",
        action="store_true",
        help="Submit generated CSV to Kaggle using Kaggle CLI.",
    )
    parser.add_argument(
        "--submission-message",
        default="TOPHAT ASIC depth-3 demo",
        help="Message used for Kaggle submission when --submit is set.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for training and CV splitting.",
    )
    return parser.parse_args()


def _run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def maybe_download_data(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    _run_cmd(["kaggle", "competitions", "download", "-c", COMPETITION, "-p", str(data_dir), "--force"])

    zip_candidates = sorted(data_dir.glob("*.zip"))
    if not zip_candidates:
        raise RuntimeError(f"Kaggle download did not produce a zip file in {data_dir}")

    zip_path = zip_candidates[-1]
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(data_dir)


def load_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_path = data_dir / "train.csv"
    test_path = data_dir / "test.csv"

    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(
            f"Missing {train_path} or {test_path}. "
            "Use --download or place Kaggle CSV files in --data-dir."
        )

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    if "Survived" not in train_df.columns:
        raise ValueError("train.csv missing Survived column")

    return train_df, test_df


def engineer_features(
    df: pd.DataFrame,
    *,
    age_fill: float,
    fare_fill: float,
) -> pd.DataFrame:
    embarked = df["Embarked"].fillna("S").map({"S": 0.0, "C": 1.0, "Q": 2.0}).fillna(0.0)
    sibsp = df["SibSp"].fillna(0).astype(float)
    parch = df["Parch"].fillna(0).astype(float)

    return pd.DataFrame(
        {
            "pclass": df["Pclass"].fillna(3).astype(float),
            "sex_male": (df["Sex"].fillna("male") == "male").astype(float),
            "age": df["Age"].fillna(age_fill).astype(float),
            "sibsp": sibsp,
            "parch": parch,
            "fare": df["Fare"].fillna(fare_fill).astype(float),
            "embarked": embarked.astype(float),
            "is_alone": ((sibsp + parch) == 0).astype(float),
        }
    )[FEATURE_NAMES]


def fit_quantize_stats(train_features: pd.DataFrame) -> dict[str, ScaleStats]:
    stats: dict[str, ScaleStats] = {}
    for name in FEATURE_NAMES:
        stats[name] = ScaleStats(
            minimum=float(train_features[name].min()),
            maximum=float(train_features[name].max()),
        )
    return stats


def quantize_features(features: pd.DataFrame, stats: dict[str, ScaleStats]) -> np.ndarray:
    out = np.zeros((features.shape[0], FEATURE_VECTOR_BYTES), dtype=np.uint8)
    for idx, name in enumerate(FEATURE_NAMES):
        col = features[name].to_numpy(dtype=np.float64, copy=True)
        lo = stats[name].minimum
        hi = stats[name].maximum
        if hi <= lo:
            q = np.zeros_like(col, dtype=np.uint8)
        else:
            q = np.round((col - lo) * 255.0 / (hi - lo)).clip(0, 255).astype(np.uint8)
        out[:, idx] = q
    return out


def train_tree(train_u8: np.ndarray, y: pd.Series, seed: int) -> tuple[DecisionTreeClassifier, dict[str, float]]:
    model = DecisionTreeClassifier(max_depth=TREE_DEPTH, random_state=seed)
    model.fit(train_u8, y.to_numpy(dtype=int))

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    cv_accuracy = cross_val_score(model, train_u8, y, cv=cv, scoring="accuracy")
    cv_auc = cross_val_score(model, train_u8, y, cv=cv, scoring="roc_auc")

    metrics = {
        "cv_accuracy_mean": float(cv_accuracy.mean()),
        "cv_accuracy_std": float(cv_accuracy.std()),
        "cv_roc_auc_mean": float(cv_auc.mean()),
        "cv_roc_auc_std": float(cv_auc.std()),
    }
    return model, metrics


def _is_leaf(tree, node_idx: int) -> bool:
    return int(tree.children_left[node_idx]) == int(tree.children_right[node_idx])


def _leaf_class(tree, node_idx: int) -> int:
    return int(np.argmax(tree.value[node_idx][0]))


def serialize_compact_tree(model: DecisionTreeClassifier) -> bytes:
    tree = model.tree_
    node_feature = np.zeros(NUM_INTERNAL, dtype=np.uint8)
    node_threshold = np.zeros(NUM_INTERNAL, dtype=np.uint8)
    leaf_values = np.zeros(NUM_LEAVES, dtype=np.uint8)

    def fill(full_node_idx: int, depth: int, sk_node_idx: int) -> None:
        if depth == TREE_DEPTH:
            leaf_values[full_node_idx - NUM_INTERNAL] = _leaf_class(tree, sk_node_idx) & 0xFF
            return

        if _is_leaf(tree, sk_node_idx):
            node_feature[full_node_idx] = 0
            node_threshold[full_node_idx] = 255
            next_left = (full_node_idx * 2) + 1
            next_right = next_left + 1
            fill(next_left, depth + 1, sk_node_idx)
            fill(next_right, depth + 1, sk_node_idx)
            return

        feature = int(tree.feature[sk_node_idx])
        if not (0 <= feature < FEATURE_VECTOR_BYTES):
            raise ValueError(f"Unexpected feature index in trained tree: {feature}")

        threshold = int(np.floor(float(tree.threshold[sk_node_idx])))
        threshold = max(0, min(255, threshold))

        node_feature[full_node_idx] = feature
        node_threshold[full_node_idx] = threshold

        next_left = (full_node_idx * 2) + 1
        next_right = next_left + 1
        fill(next_left, depth + 1, int(tree.children_left[sk_node_idx]))
        fill(next_right, depth + 1, int(tree.children_right[sk_node_idx]))

    fill(0, 0, 0)

    image = bytearray()
    for idx in range(NUM_INTERNAL):
        image.extend([int(node_feature[idx]), int(node_threshold[idx])])
    for idx in range(NUM_LEAVES):
        image.append(int(leaf_values[idx]))

    if len(image) != MODEL_IMAGE_BYTES:
        raise ValueError(f"Serialized model length {len(image)} != expected {MODEL_IMAGE_BYTES}")

    return bytes(image)


def predict_compact_model(model_bytes: bytes, features_u8: np.ndarray) -> np.ndarray:
    if len(model_bytes) != MODEL_IMAGE_BYTES:
        raise ValueError(f"model_bytes must be {MODEL_IMAGE_BYTES} bytes")

    node_feature = np.frombuffer(model_bytes[: NUM_INTERNAL * 2 : 2], dtype=np.uint8)
    node_threshold = np.frombuffer(model_bytes[1 : NUM_INTERNAL * 2 : 2], dtype=np.uint8)
    leaf_values = np.frombuffer(model_bytes[NUM_INTERNAL * 2 :], dtype=np.uint8)

    preds = np.zeros(features_u8.shape[0], dtype=np.uint8)

    for row_idx, row in enumerate(features_u8):
        node = 0
        for depth in range(TREE_DEPTH):
            feat_idx = int(node_feature[node])
            threshold = int(node_threshold[node])
            branch_right = 1 if int(row[feat_idx]) > threshold else 0
            child = (node * 2) + 1 + branch_right

            if depth == (TREE_DEPTH - 1):
                preds[row_idx] = leaf_values[child - NUM_INTERNAL]
            else:
                node = child

    return preds


def predict_with_board(port: str, model_bytes: bytes, features_u8: np.ndarray) -> tuple[list[int], dict[str, Any]]:
    with JsonLineSerialTransport(port) as transport:
        client = TophatClient(transport)
        ping = client.ping()
        init_error = ping.get("init_error")
        if isinstance(init_error, str) and init_error:
            raise RuntimeError(f"RP2040 bridge reported init_error: {init_error}")
        client.clear()
        client.load_model(model_bytes)

        preds: list[int] = []
        total = features_u8.shape[0]
        for idx, row in enumerate(features_u8):
            preds.append(int(client.predict(row.tolist())))
            if (idx + 1) % 50 == 0 or (idx + 1) == total:
                print(f"[board] predicted {idx + 1}/{total}")

    return preds, ping


def write_submission(passenger_ids: pd.Series, predictions: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["PassengerId", "Survived"])
        for pid, pred in zip(passenger_ids.astype(int), predictions.astype(int), strict=True):
            writer.writerow([int(pid), int(pred)])


def submit_to_kaggle(submission_csv: Path, message: str) -> dict[str, str]:
    submit = _run_cmd(
        [
            "kaggle",
            "competitions",
            "submit",
            "-c",
            COMPETITION,
            "-f",
            str(submission_csv),
            "-m",
            message,
        ]
    )
    submissions = _run_cmd(["kaggle", "competitions", "submissions", "-c", COMPETITION])
    return {
        "submit_stdout": submit.stdout.strip(),
        "submit_stderr": submit.stderr.strip(),
        "submissions_stdout": submissions.stdout.strip(),
    }


def main() -> None:
    args = parse_args()

    if not args.skip_board and not args.port:
        raise SystemExit("--port is required unless --skip-board is set.")

    if args.download:
        print(f"[data] downloading Kaggle {COMPETITION} CSVs into {args.data_dir}")
        maybe_download_data(args.data_dir)

    train_df, test_df = load_data(args.data_dir)

    age_median = float(train_df["Age"].median())
    fare_median = float(train_df["Fare"].median())

    train_features = engineer_features(train_df, age_fill=age_median, fare_fill=fare_median)
    test_features = engineer_features(test_df, age_fill=age_median, fare_fill=fare_median)
    y = train_df["Survived"].astype(int)

    stats = fit_quantize_stats(train_features)
    train_u8 = quantize_features(train_features, stats)
    test_u8 = quantize_features(test_features, stats)

    model, metrics = train_tree(train_u8, y, args.seed)
    model_bytes = serialize_compact_tree(model)
    sw_preds = predict_compact_model(model_bytes, test_u8)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "titanic_model_22b.bin"
    scaler_path = args.output_dir / "feature_scaler.json"
    submission_path = args.output_dir / "submission_asic.csv"
    report_path = args.output_dir / "demo_report.json"

    model_path.write_bytes(model_bytes)
    scaler_payload = {name: asdict(stats[name]) for name in FEATURE_NAMES}
    scaler_path.write_text(json.dumps(scaler_payload, indent=2))

    board_ping: dict[str, Any] | None = None
    board_preds_np: np.ndarray | None = None
    mismatch_count: int | None = None

    if args.skip_board:
        print("[board] skipped; writing software-only submission")
        board_preds_np = sw_preds
        mismatch_count = 0
    else:
        print(f"[board] running {test_u8.shape[0]} predictions via {args.port}")
        board_preds, board_ping = predict_with_board(args.port, model_bytes, test_u8)
        board_preds_np = np.array(board_preds, dtype=np.uint8)
        mismatch_count = int(np.count_nonzero(board_preds_np != sw_preds))
        print(f"[board] software vs board mismatches: {mismatch_count}")

    assert board_preds_np is not None
    write_submission(test_df["PassengerId"], board_preds_np, submission_path)

    kaggle_submit: dict[str, str] | None = None
    if args.submit:
        print("[kaggle] submitting...")
        kaggle_submit = submit_to_kaggle(submission_path, args.submission_message)
        if kaggle_submit.get("submit_stdout"):
            print(kaggle_submit["submit_stdout"])
        if kaggle_submit.get("submissions_stdout"):
            print(kaggle_submit["submissions_stdout"])

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "competition": COMPETITION,
        "data_dir": str(args.data_dir),
        "output_dir": str(args.output_dir),
        "rows": {
            "train": int(train_df.shape[0]),
            "test": int(test_df.shape[0]),
        },
        "feature_names": FEATURE_NAMES,
        "metrics": metrics,
        "artifacts": {
            "model_bytes": str(model_path),
            "feature_scaler": str(scaler_path),
            "submission": str(submission_path),
            "report": str(report_path),
        },
        "board": {
            "used": not args.skip_board,
            "port": args.port,
            "ping": board_ping,
            "software_vs_board_mismatch_count": mismatch_count,
        },
        "kaggle_submit": kaggle_submit,
    }
    report_path.write_text(json.dumps(report, indent=2))

    print("[done]")
    print(f"model bytes: {model_path} ({len(model_bytes)} bytes)")
    print(f"submission: {submission_path}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
