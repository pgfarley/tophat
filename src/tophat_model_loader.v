/*
 * Copyright (c) 2026 Patrick Farley
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tophat_model_loader #(
    parameter integer NUM_INTERNAL = 7,
    parameter integer NUM_LEAVES = 8,
    parameter integer FEATURE_IDX_W = 3
) (
    input  wire                            clk,
    input  wire                            rst_n,
    input  wire                            clear_i,
    input  wire                            model_byte_valid_i,
    input  wire [7:0]                      model_byte_i,
    output reg                             model_loaded_o,
    output reg [NUM_INTERNAL*FEATURE_IDX_W-1:0] node_feature_o,
    output reg [NUM_INTERNAL*8-1:0]        node_threshold_o,
    output reg [NUM_LEAVES*8-1:0]          leaf_value_o
);

  localparam integer INTERNAL_BYTES = NUM_INTERNAL * 2;
  localparam integer MODEL_BYTES = INTERNAL_BYTES + NUM_LEAVES;
  localparam integer BYTE_IDX_W = (MODEL_BYTES <= 1) ? 1 : $clog2(MODEL_BYTES);
  localparam integer NODE_IDX_W = (NUM_INTERNAL <= 1) ? 1 : $clog2(NUM_INTERNAL);
  localparam integer LEAF_IDX_W = (NUM_LEAVES <= 1) ? 1 : $clog2(NUM_LEAVES);

  reg [BYTE_IDX_W-1:0] byte_idx_q;

  wire [NODE_IDX_W-1:0] node_idx_w;
  wire field_idx_w;
  wire [LEAF_IDX_W-1:0] leaf_idx_w;
  assign node_idx_w = byte_idx_q >> 1;
  assign field_idx_w = byte_idx_q[0];
  /* verilator lint_off WIDTHEXPAND */
  /* verilator lint_off WIDTHTRUNC */
  assign leaf_idx_w = byte_idx_q - INTERNAL_BYTES;
  /* verilator lint_on WIDTHTRUNC */
  /* verilator lint_on WIDTHEXPAND */

  always @(posedge clk) begin
    if (~rst_n || clear_i) begin
      byte_idx_q       <= {BYTE_IDX_W{1'b0}};
      model_loaded_o   <= 1'b0;
      node_feature_o   <= {(NUM_INTERNAL*FEATURE_IDX_W){1'b0}};
      node_threshold_o <= {(NUM_INTERNAL*8){1'b0}};
      leaf_value_o     <= {(NUM_LEAVES*8){1'b0}};
    end else if (model_byte_valid_i) begin
      if (byte_idx_q == {BYTE_IDX_W{1'b0}}) begin
        model_loaded_o <= 1'b0;
      end

      /* verilator lint_off WIDTHEXPAND */
      if (byte_idx_q < INTERNAL_BYTES) begin
      /* verilator lint_on WIDTHEXPAND */
        if (field_idx_w == 1'b0) begin
          node_feature_o[(node_idx_w*FEATURE_IDX_W) +: FEATURE_IDX_W] <= model_byte_i[FEATURE_IDX_W-1:0];
        end else begin
          node_threshold_o[(node_idx_w*8) +: 8] <= model_byte_i;
        end
      /* verilator lint_off WIDTHEXPAND */
      end else if (byte_idx_q < MODEL_BYTES) begin
      /* verilator lint_on WIDTHEXPAND */
        leaf_value_o[(leaf_idx_w*8) +: 8] <= model_byte_i;
      end

      /* verilator lint_off WIDTHEXPAND */
      if (byte_idx_q == (MODEL_BYTES - 1)) begin
      /* verilator lint_on WIDTHEXPAND */
        byte_idx_q     <= {BYTE_IDX_W{1'b0}};
        model_loaded_o <= 1'b1;
      end else begin
        byte_idx_q <= byte_idx_q + {{(BYTE_IDX_W-1){1'b0}}, 1'b1};
      end
    end
  end

endmodule
