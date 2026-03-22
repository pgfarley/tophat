# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
FST ?= -fst # Use more efficient FST format
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
PROJECT_SOURCES = \
	tt_um_pgfarley_tophat_top.v \
	tophat_io_intf.v \
	tophat_model_loader.v \
	tophat_feature_loader.v \
	tophat_tree_core.v \
	tophat_result_if.v

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD				= sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

# Gate level simulation:
SIM_BUILD				= sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_io/verilog/sg13g2_io.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

# Allow sharing configuration between design and testbench via `include`:
COMPILE_ARGS 		+= -I$(SRC_DIR)

# Include the testbench sources:
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL = tb

# List test modules to run, separated by commas and without the .py suffix.
# Keep this list space-free: a space after ',' breaks the env-var assignment in Makefile.sim.
COCOTB_TEST_MODULES = test
COCOTB_MAKEFILE = $(shell cocotb-config --makefiles 2>/dev/null)/Makefile.sim

.PHONY: test-cocotb test-python test-all
PYTHON ?= ../.venv/bin/python
PYTEST ?= $(PYTHON) -m pytest

test-cocotb:
	$(MAKE) sim

test-python:
	$(PYTEST) -q .

test-all:
	$(MAKE) clean
	$(MAKE) test-cocotb
	$(MAKE) test-python

# Let cocotb own the simulator targets. Guard the include so `make test-python`
# still works even when cocotb isn't installed in the active environment.
ifneq ($(wildcard $(COCOTB_MAKEFILE)),)
include $(COCOTB_MAKEFILE)
endif
