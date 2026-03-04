# TOPHAT Host Serial RPC

This document defines a practical laptop-to-board flow:

1. Laptop Python client talks over USB CDC serial.
2. RP2040 firmware exposes a newline-delimited JSON RPC bridge.
3. RP2040 bridge drives the TOPHAT project pins (`ui_in`, `uio_in`) and reads status/result (`uio_out`, `uo_out`).

The host utility for this flow is [`tools/host/tophat_host.py`](../tools/host/tophat_host.py).
Install host dependency:

```sh
pip install pyserial
```

## Request/Response Format

- Each request is one JSON object per line.
- Each response is one JSON object per line.
- Every response must include `ok: true|false`.
- Error responses use `{"ok": false, "error": "<message>"}`.

## Commands

### `ping`

Request:

```json
{"cmd":"ping"}
```

Response (example):

```json
{"ok":true,"bridge":"tophat-rpc","protocol":1}
```

### `clear`

Request:

```json
{"cmd":"clear"}
```

Response:

```json
{"ok":true}
```

### `load_model`

Request:

```json
{"cmd":"load_model","model":[0,1,2,...]}
```

Notes:
- `model` must be exactly 22 unsigned bytes.
- Matches the model format documented in [`docs/info.md`](info.md).

Response:

```json
{"ok":true}
```

### `load_features`

Request:

```json
{"cmd":"load_features","features":[4,6,10,...]}
```

Notes:
- `features` must be exactly 8 unsigned bytes.

Response:

```json
{"ok":true}
```

### `run`

Request:

```json
{"cmd":"run"}
```

Response:

```json
{"ok":true,"prediction":42}
```

### `predict`

Request:

```json
{"cmd":"predict","features":[4,6,10,...]}
```

Behavior:
- Equivalent to `load_features` followed by `run`.

Response:

```json
{"ok":true,"prediction":42}
```

## Host CLI Examples

Model load:

```sh
python tools/host/tophat_host.py load-model --port /dev/ttyACM0 --model test/golden_model.bin
```

Single prediction with comma-separated features:

```sh
python tools/host/tophat_host.py predict --port /dev/ttyACM0 --features 4,6,10,12,15,20,10,18
```

Split flow (feature load then run):

```sh
python tools/host/tophat_host.py load-features --port /dev/ttyACM0 --features-file features.json
python tools/host/tophat_host.py run --port /dev/ttyACM0
```
