![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# TOPHAT: TapeOut Prediction with Hardware Acceleration for Trees

A hardware decision-tree inference engine for a fixed depth-3 tree (7 internal nodes, 8 leaves) with 8 input features. The documentation can be found [here](docs/info.md).

TOPHAT is implemented as a Tiny Tapeout project. Tiny Tapeout is an educational project that aims to make it easier and cheaper than ever to get your digital and analog designs manufactured on a real chip. To learn more and get started, visit https://tinytapeout.com.

## Local test run

```sh
source .venv/bin/activate
make -C test test-all
```

## Board example package

Deployable MicroPython example code lives in [`examples/`](examples/README.md), structured to match TinyTapeout firmware `src/examples`.
