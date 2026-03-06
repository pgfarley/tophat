# Titanic On TOPHAT ASIC Demo

This is an end-to-end "because it's cool" demo pipeline:

1. Get Kaggle Titanic data.
2. Train a model that fits TOPHAT constraints (single depth-3 tree, 8 features, 8-bit values).
3. Serialize and upload the model to the board.
4. Run Kaggle `test.csv` inference on the ASIC.
5. Write a Kaggle submission CSV and optionally submit it.

## Prerequisites

- RP2040 bridge running on the board (`tools/rp2040/main.py` copied to `:main.py`).
- Host Python deps for demo script:

```sh
pip install pandas scikit-learn pyserial kaggle
```

- Kaggle credentials configured (for `--download` and/or `--submit`).

## One-Command Demo

From repo root:

```sh
python tools/demo/titanic_asic_demo.py \
  --port /dev/ttyACM0 \
  --data-dir ../titanic-xgboost/data/raw \
  --output-dir outputs/titanic_asic_demo \
  --download \
  --submit \
  --submission-message "TOPHAT ASIC depth-3 demo"
```

What this writes:

- `outputs/titanic_asic_demo/titanic_model_22b.bin`
- `outputs/titanic_asic_demo/feature_scaler.json`
- `outputs/titanic_asic_demo/submission_asic.csv`
- `outputs/titanic_asic_demo/demo_report.json`

## Useful Variants

Train + run on board, but do not submit:

```sh
python tools/demo/titanic_asic_demo.py \
  --port /dev/ttyACM0 \
  --data-dir ../titanic-xgboost/data/raw \
  --output-dir outputs/titanic_asic_demo
```

Train and generate software-only submission (no board):

```sh
python tools/demo/titanic_asic_demo.py \
  --skip-board \
  --data-dir ../titanic-xgboost/data/raw \
  --output-dir outputs/titanic_asic_demo
```

## Notes

- The demo intentionally keeps model shape fixed to hardware constraints:
  - depth `3`
  - `7` internal nodes
  - `8` leaves
  - `22` serialized bytes
- Board run includes a software-vs-board mismatch count in `demo_report.json` to sanity-check transport + inference correctness.
