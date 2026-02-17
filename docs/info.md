# TOPHAT: Tapeout Prediction with Hardware Acceleration for Trees

TOPHAT is a hardware decision-tree inference engine for a fixed depth-3 tree (7 internal nodes, 8 leaves) with 8 input features.

## Usage

### Background

A decision tree is a supervised learning model that predicts an output by applying a sequence of simple feature-based tests (for example, `feature_i < threshold`). Training determines which tests to use and where to place them so the model separates examples effectively.

At inference time, prediction traverses from the root to a leaf based on comparison results. In hardware, the model is represented as fixed node parameters plus deterministic control flow.

For a well-known example of the kind of problem to which a decision tree can be applied, see Kaggle's [Titanic - Machine Learning from Disaster](https://www.kaggle.com/competitions/titanic).

### Model Representation

TOPHAT consumes a fixed 36-byte model image:

- Bytes 0..27: 7 internal nodes, 4 bytes per node in the order [feature_id, threshold, left_child, right_child]
- Bytes 28..35: 8 leaf values, 1 byte per leaf

| Field | Bits | Note |
| --- | --- | --- |
| feature_id | 3 | Supports 8 features |
| threshold | 8 | Unsigned |
| left_child | 4 | 0..6 = internal node, 7..14 = leaf node |
| right_child | 4 | Same encoding as left_child |

#### Example Model Serialization

Any model can be used as long as it is serialized into the format above. The example below was generated with scikit-learn. See `test/generate_golden_tree.py` for details. For more background on scikit-learn trees, see the [scikit-learn Decision Trees documentation](https://scikit-learn.org/stable/modules/tree.html).

![Sample TOPHAT tree and indices](assets/model-serialization-tree.svg)

| Byte Range | Record | Decoded | Hex Bytes |
| --- | --- | --- | --- |
| 0..3 | N0 | [feature=2, threshold=24, left=1, right=2] | 02 18 01 02 |
| 4..7 | N1 | [feature=0, threshold=8, left=3, right=4] | 00 08 03 04 |
| 8..11 | N2 | [feature=7, threshold=35, left=5, right=6] | 07 23 05 06 |
| 12..15 | N3 | [feature=4, threshold=20, left=7, right=8] | 04 14 07 08 |
| 16..19 | N4 | [feature=1, threshold=20, left=9, right=10] | 01 14 09 0A |
| 20..23 | N5 | [feature=6, threshold=40, left=11, right=12] | 06 28 0B 0C |
| 24..27 | N6 | [feature=3, threshold=28, left=13, right=14] | 03 1C 0D 0E |
| 28..35 | Leaves | [L0..L7] output values | 08 12 19 2D 37 55 5F 8C |

### Feature Representation

Lorem ipsum dolor.

### Control Protocol

#### Loading a Model

Lorem ipsum dolor.

#### Prediction

Lorem ipsum dolor.

## How It Works

### Block Diagram

Lorem ipsum dolor.

### Module Descriptions

Lorem ipsum dolor.

## How to Test

Lorem ipsum dolor.

## Acknowledgments

Thanks to [BLAKE2s Hashing Accelerator: A Solo Tapeout Journey](https://essenceia.github.io/projects/blake2s_hashing_accelerator_a_solo_tapeout_journey/) for the inspiration.
