# TOPHAT Host Serial RPC

This flow has two pieces:

1. Host CLI: [`tools/host/tophat_host.py`](../tools/host/tophat_host.py)
2. RP2040 bridge: [`tools/rp2040/main.py`](../tools/rp2040/main.py)

The host sends JSON lines over USB CDC serial. The RP2040 bridge receives those requests, drives TOPHAT pins, and returns JSON line responses.

## Install And Deploy

Host dependency:

```sh
pip install pyserial
```

Deploy bridge to board as `:main.py`:

```sh
mpremote connect /dev/ttyACM0 cp tools/rp2040/main.py :main.py
mpremote connect /dev/ttyACM0 reset
```

Notes:
- The bridge configures `ASIC_RP_CONTROL` mode and sets `uio_oe_pico=0x07` so RP2040 drives `uio[2:0]` (`valid + cmd`).
- Startup chatter is redirected to `tophat_boot.log` during bootstrap.
- You can inspect that log with:

```sh
mpremote connect /dev/ttyACM0 fs cat :tophat_boot.log
```

## Wire Protocol

- One request JSON object per line.
- One response JSON object per line.
- Every valid response includes `ok: true|false`.
- Error responses use `{"ok": false, "error": "<message>"}`.

## Commands

### `ping`

Request:

```json
{"cmd":"ping"}
```

Response (example):

```json
{"ok":true,"protocol_version":1,"project_enabled":"FPGA:tt_um_pgfarley_tophat_top","mode":"ASIC_RP_CONTROL"}
```

If bridge init failed, response still includes `ok: true` plus `init_error`.

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

Rules:
- `model` must be exactly 22 unsigned bytes.
- Model format is documented in [`docs/info.md`](info.md).

Response:

```json
{"ok":true}
```

### `load_features`

Request:

```json
{"cmd":"load_features","features":[4,6,10,...]}
```

Rules:
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
- Equivalent to `load_features` then `run`.

Response:

```json
{"ok":true,"prediction":42}
```

## Host CLI Usage

Ping:

```sh
python tools/host/tophat_host.py ping --port /dev/ttyACM0
```

Clear state:

```sh
python tools/host/tophat_host.py clear --port /dev/ttyACM0
```

Load model:

```sh
python tools/host/tophat_host.py load-model --port /dev/ttyACM0 --model test/golden_model.bin
```

Predict from CSV features:

```sh
python tools/host/tophat_host.py predict --port /dev/ttyACM0 --features 4,6,10,12,15,20,10,18
```

Split flow (`load-features` then `run`):

```sh
python tools/host/tophat_host.py load-features --port /dev/ttyACM0 --features-file features.json
python tools/host/tophat_host.py run --port /dev/ttyACM0
```

## Quick End-To-End

```sh
python tools/host/tophat_host.py ping --port /dev/ttyACM0
python tools/host/tophat_host.py clear --port /dev/ttyACM0
python tools/host/tophat_host.py load-model --port /dev/ttyACM0 --model test/golden_model.bin
python tools/host/tophat_host.py predict --port /dev/ttyACM0 --features 4,6,10,12,15,20,10,18
```
