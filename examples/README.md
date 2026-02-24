# TOPHAT Example Packages

This directory mirrors the TinyTapeout MicroPython firmware `src/examples` layout.

`tt_um_pgfarley_tophat` is a deployable package that can be copied to a TinyTapeout firmware checkout and run directly on a board.

## Local workflow

From this repository root:

```sh
source .venv/bin/activate
make -C test test-all
```

`test-all` runs:

1. cocotb RTL tests (`test.py`)
2. pytest checks (including validation that this `examples/` package matches local fixtures/model bytes)

## Deploy to TinyTapeout firmware checkout

Assume your firmware checkout is at `$FW_ROOT`.

```sh
git -C "$FW_ROOT" pull
mkdir -p "$FW_ROOT/src/examples/tt_um_pgfarley_tophat"
rsync -a --delete ./examples/tt_um_pgfarley_tophat/ "$FW_ROOT/src/examples/tt_um_pgfarley_tophat/"
```

On the board REPL:

```python
import examples.tt_um_pgfarley_tophat as tophat_example
tophat_example.run()
```
