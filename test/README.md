
## How to run

To run the RTL simulation:

```sh
make -B
```

To run all local checks (RTL cocotb + python tests):

```sh
make test-all
```

To run gatelevel simulation, first harden your project and copy `../runs/wokwi/results/final/verilog/gl/{your_module_name}.v` to `gate_level_netlist.v`.

Then run:

```sh
make -B GATES=yes
```
