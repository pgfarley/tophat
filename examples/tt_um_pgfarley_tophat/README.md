# `tt_um_pgfarley_tophat` board example

This package provides a hardware-in-the-loop microcotb test for TOPHAT that:

1. resets the design,
2. sends a fixed 36-byte model image,
3. sends fixture feature vectors, and
4. asserts prediction bytes against fixed expected fixture values.

## Files

- `__init__.py`: exports `run()`
- `tt_um_pgfarley_tophat.py`: microcotb tests + TinyTapeout runner setup
- `fixture_data.py`: fixed feature fixtures and expected predictions
- `model_image.py`: fixed serialized model bytes

## Run on board

```python
import examples.tt_um_pgfarley_tophat as tophat_example
tophat_example.run()
```
