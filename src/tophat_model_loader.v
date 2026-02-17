/*
 * Copyright (c) 2026 Patrick Farley
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tophat_model_loader #(
    parameter integer NUM_INTERNAL = 7,
    parameter integer NUM_LEAVES = 8
) (
    input  wire                            clk,
    input  wire                            rst_n,
    input  wire                            clear_i,
    input  wire                            model_byte_valid_i,
    input  wire [7:0]                      model_byte_i,
    output reg                             model_loaded_o,
    output reg [NUM_INTERNAL*3-1:0]        node_feature_o,
    output reg [NUM_INTERNAL*8-1:0]        node_threshold_o,
    output reg [NUM_INTERNAL*4-1:0]        node_left_o,
    output reg [NUM_INTERNAL*4-1:0]        node_right_o,
    output reg [NUM_LEAVES*8-1:0]          leaf_value_o
);

  localparam integer INTERNAL_BYTES = NUM_INTERNAL * 4;
  localparam integer MODEL_BYTES = INTERNAL_BYTES + NUM_LEAVES;
  localparam integer BYTE_IDX_W = 6;

  reg [BYTE_IDX_W-1:0] byte_idx_q;

  wire [2:0] node_idx_w;
  wire [1:0] field_idx_w;
  wire [2:0] leaf_idx_w;
  assign node_idx_w = byte_idx_q[4:2];
  assign field_idx_w = byte_idx_q[1:0];
  /* verilator lint_off WIDTHEXPAND */
  assign leaf_idx_w = byte_idx_q - INTERNAL_BYTES;
  /* verilator lint_on WIDTHEXPAND */

  always @(posedge clk) begin
    if (~rst_n || clear_i) begin
      byte_idx_q       <= {BYTE_IDX_W{1'b0}};
      model_loaded_o   <= 1'b0;
      node_feature_o   <= {(NUM_INTERNAL*3){1'b0}};
      node_threshold_o <= {(NUM_INTERNAL*8){1'b0}};
      node_left_o      <= {(NUM_INTERNAL*4){1'b0}};
      node_right_o     <= {(NUM_INTERNAL*4){1'b0}};
      leaf_value_o     <= {(NUM_LEAVES*8){1'b0}};
    end else if (model_byte_valid_i) begin
      if (byte_idx_q == {BYTE_IDX_W{1'b0}}) begin
        model_loaded_o <= 1'b0;
      end

      /* verilator lint_off WIDTHEXPAND */
      if (byte_idx_q < INTERNAL_BYTES) begin
      /* verilator lint_on WIDTHEXPAND */
        case (field_idx_w)
          2'd0: node_feature_o[(node_idx_w*3) +: 3] <= model_byte_i[2:0];
          2'd1: node_threshold_o[(node_idx_w*8) +: 8] <= model_byte_i;
          2'd2: node_left_o[(node_idx_w*4) +: 4] <= model_byte_i[3:0];
          default: node_right_o[(node_idx_w*4) +: 4] <= model_byte_i[3:0];
        endcase
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
