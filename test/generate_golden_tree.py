#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2026
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import numpy as np
import joblib
from sklearn.tree import DecisionTreeRegressor, _tree

# Feature order (index -> name):
# 0 budget_10m
# 1 marketing_5m
# 2 franchise_strength
# 3 star_power
# 4 critic_buzz
# 5 family_friendliness (unused)
# 6 release_timing
# 7 screen_count_100

# Depth-3 regression tree with fixed thresholds:
# Root: f2 <= 24
# Left: f0 <= 8
# Right: f7 <= 35
# And so on (see node setup below).

LEAF_VALUES = {
    "L0": 8,
    "L1": 18,
    "L2": 25,
    "L3": 45,
    "L4": 55,
    "L5": 85,
    "L6": 95,
    "L7": 140,
}


def _build_tree() -> DecisionTreeRegressor:
    n_features = 8
    n_outputs = 1
    n_nodes = 15  # full binary tree with depth 3

    tree = _tree.Tree(n_features, np.array([1], dtype=np.intp), n_outputs)
    state = tree.__getstate__()
    nodes = np.zeros(n_nodes, dtype=state["nodes"].dtype)
    values = np.zeros((n_nodes, n_outputs, 1), dtype=np.float64)

    TREE_LEAF = _tree.TREE_LEAF
    TREE_UNDEFINED = _tree.TREE_UNDEFINED

    def set_node(i: int, feature: int, threshold: float, left: int, right: int) -> None:
        nodes[i]["left_child"] = left
        nodes[i]["right_child"] = right
        nodes[i]["feature"] = feature
        nodes[i]["threshold"] = float(threshold)
        nodes[i]["impurity"] = 0.0
        nodes[i]["n_node_samples"] = 1
        nodes[i]["weighted_n_node_samples"] = 1.0
        if "missing_go_to_left" in nodes.dtype.names:
            nodes[i]["missing_go_to_left"] = 1

    def set_leaf(i: int, value: float) -> None:
        nodes[i]["left_child"] = TREE_LEAF
        nodes[i]["right_child"] = TREE_LEAF
        nodes[i]["feature"] = TREE_UNDEFINED
        nodes[i]["threshold"] = -2.0
        nodes[i]["impurity"] = 0.0
        nodes[i]["n_node_samples"] = 1
        nodes[i]["weighted_n_node_samples"] = 1.0
        if "missing_go_to_left" in nodes.dtype.names:
            nodes[i]["missing_go_to_left"] = 1
        values[i, 0, 0] = float(value)

    # Internal nodes
    set_node(0, 2, 24, 1, 2)   # franchise_strength
    set_node(1, 0, 8, 3, 4)    # budget_10m
    set_node(2, 7, 35, 5, 6)   # screen_count_100
    set_node(3, 4, 20, 7, 8)   # critic_buzz
    set_node(4, 1, 20, 9, 10)  # marketing_5m
    set_node(5, 6, 40, 11, 12) # release_timing
    set_node(6, 3, 28, 13, 14) # star_power

    # Leaves
    set_leaf(7, LEAF_VALUES["L0"])
    set_leaf(8, LEAF_VALUES["L1"])
    set_leaf(9, LEAF_VALUES["L2"])
    set_leaf(10, LEAF_VALUES["L3"])
    set_leaf(11, LEAF_VALUES["L4"])
    set_leaf(12, LEAF_VALUES["L5"])
    set_leaf(13, LEAF_VALUES["L6"])
    set_leaf(14, LEAF_VALUES["L7"])

    def propagate_values(node: int) -> float:
        left = nodes[node]["left_child"]
        right = nodes[node]["right_child"]
        if left == TREE_LEAF and right == TREE_LEAF:
            return values[node, 0, 0]
        left_val = propagate_values(left)
        right_val = propagate_values(right)
        values[node, 0, 0] = 0.5 * (left_val + right_val)
        return values[node, 0, 0]

    propagate_values(0)

    state["max_depth"] = 3
    state["node_count"] = n_nodes
    state["nodes"] = nodes
    state["values"] = values
    tree.__setstate__(state)

    clf = DecisionTreeRegressor()
    clf.tree_ = tree
    clf.n_features_in_ = n_features
    clf.n_outputs_ = 1
    return clf


def serialize_tree_to_model_bytes(clf: DecisionTreeRegressor) -> bytes:
    """
    Serialize tree into the fixed 36-byte image expected by tophat_model_loader:
    - 7 internal nodes * 4 bytes: [feature, threshold, left, right]
    - 8 leaves * 1 byte: [value]
    """
    tree = clf.tree_
    num_internal = 7
    num_leaves = 8
    leaf_base = 7

    data = bytearray()

    for node_idx in range(num_internal):
        feature = int(tree.feature[node_idx])
        threshold_f = float(tree.threshold[node_idx])
        left = int(tree.children_left[node_idx])
        right = int(tree.children_right[node_idx])

        threshold = int(round(threshold_f))
        if abs(threshold_f - threshold) > 1e-6:
            raise ValueError(
                f"Node {node_idx} threshold is not integer-like: {threshold_f}"
            )

        if not (0 <= feature <= 7):
            raise ValueError(f"Node {node_idx} feature out of range: {feature}")
        if not (0 <= threshold <= 255):
            raise ValueError(f"Node {node_idx} threshold out of range: {threshold}")
        if not (0 <= left <= 15 and 0 <= right <= 15):
            raise ValueError(
                f"Node {node_idx} child index out of 4-bit range: left={left}, right={right}"
            )

        data.extend([feature & 0x07, threshold & 0xFF, left & 0x0F, right & 0x0F])

    for node_idx in range(leaf_base, leaf_base + num_leaves):
        value_f = float(tree.value[node_idx, 0, 0])
        value = int(round(value_f))
        if abs(value_f - value) > 1e-6:
            raise ValueError(f"Leaf {node_idx} value is not integer-like: {value_f}")
        if not (0 <= value <= 255):
            raise ValueError(f"Leaf {node_idx} value out of range: {value}")
        data.append(value & 0xFF)

    expected_len = (num_internal * 4) + num_leaves
    if len(data) != expected_len:
        raise ValueError(f"Model image length {len(data)} != {expected_len}")

    return bytes(data)


def write_artifacts(out_dir: Path) -> tuple[Path, Path]:
    clf = _build_tree()
    tree_path = out_dir / "golden_tree.joblib"
    model_path = out_dir / "golden_model.bin"

    joblib.dump(clf, tree_path)
    model_bytes = serialize_tree_to_model_bytes(clf)
    model_path.write_bytes(model_bytes)

    return tree_path, model_path


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    tree_path, model_path = write_artifacts(out_dir)
    print(f"Wrote {tree_path}")
    print(f"Wrote {model_path}")


if __name__ == "__main__":
    main()
