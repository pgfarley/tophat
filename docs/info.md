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

TOPHAT feature input is a fixed 8-byte vector with each feature encoded as an unsigned 8-bit value.

Example Feature Serialization

| Feature ID | Description | Hex Byte |
| --- | ---  | --- |
| 0 | budget 10m | 04 |
| 1 | marketing 5m | 06 |
| 2 | franchise strength | 0A |
| 3 | star power | 0C |
| 4 | critic buzz | 0F |
| 5 | family friendliness | 14 |
| 6 | release timing | 0A |
| 7 | screen count 100 | 12 |

### Control Protocol

TOPHAT uses a byte-wide command and payload interface:

| Signal | Direction | Description |
| --- | --- | --- |
| `ui_in[7:0]` | input | Payload byte |
| `uio_in[0]` | input | `valid` strobe |
| `uio_in[2:1]` | input | Command select |
| `uio_out[3]` | output | `ready` (`~busy`) |
| `uio_out[4]` | output | `busy` |
| `uio_out[5]` | output | `pred_valid` pulse |
| `uio_out[6]` | output | `model_loaded` |
| `uio_out[7]` | output | `error_or_missing_features` (`error | ~features_loaded`) |

A transfer is accepted on a rising clock edge only when `valid=1` and `ready=1`.

| `uio_in[2:1]` | Name | `ui_in[7:0]` payload |
| --- | --- | --- |
| `2'b00` | `CMD_MODEL` | Model byte stream |
| `2'b01` | `CMD_FEATURE` | Feature byte stream |
| `2'b10` | `CMD_CTRL` | Bit0=`run`, bit1=`clear` |
| `2'b11` | Reserved | Ignored |

#### Loading a Model

1. Wait until `ready=1`.
2. Send 36 bytes with `CMD_MODEL` (`2'b00`), one accepted transfer per byte.
3. Bytes `0..27` are node records, bytes `28..35` are leaf values. See "Model Representation" above.
4. `model_loaded` (`uio_out[6]`) asserts after byte 35 is accepted.

Notes:
- `CMD_CTRL` with `clear=1` (`ui_in[1]=1`) resets model, features, status, and core state.
- Starting a new model stream deasserts `model_loaded` until all 36 bytes are reloaded.

#### Prediction

1. Load 8 feature bytes with `CMD_FEATURE` (`2'b01`), byte 0 through byte 7. See "Feature Representation" above.
2. Wait for `ready=1`, then send `CMD_CTRL` with `run=1` (`ui_in[0]=1`).
3. If model and features are both loaded, core enters `busy=1` traversal and returns with a one-cycle `pred_valid` pulse.
4. Read prediction from `uo_out[7:0]` when `pred_valid=1`.
5. A consumed run clears `features_loaded`, so features must be reloaded before the next prediction.

| Status bit | Meaning |
| --- | --- |
| `uio_out[3]` | `ready = ~busy` |
| `uio_out[5]` | One-cycle `pred_valid` when a result is produced |
| `uio_out[7]` | `error OR ~features_loaded` |

| Run condition | Behavior |
| --- | --- |
| `model_loaded=1` and `features_loaded=1` | Normal traversal, valid prediction on `uo_out` |
| Missing model or features | Run is rejected, `error` is set |
| Invalid child index during traversal | `pred_valid` pulses with `uo_out=0` and `error=1` |

## How It Works

### Block Diagram

Lorem ipsum dolor.

### Module Descriptions

Lorem ipsum dolor.

## How to Test

Lorem ipsum dolor.

## Acknowledgments

Thanks to [BLAKE2s Hashing Accelerator: A Solo Tapeout Journey](https://essenceia.github.io/projects/blake2s_hashing_accelerator_a_solo_tapeout_journey/) for the inspiration.
