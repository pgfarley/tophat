/*
 * Copyright (c) 2026 Patrick Farley
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tophat_tree_core #(
    parameter integer NUM_FEATURES = 8,
    parameter integer NUM_INTERNAL = 7,
    parameter integer NUM_LEAVES = 8,
    parameter integer LEAF_BASE = 7
) (
    input  wire                            clk,
    input  wire                            rst_n,
    input  wire                            clear_i,
    input  wire                            run_i,
    input  wire                            model_loaded_i,
    input  wire                            features_loaded_i,
    input  wire [NUM_FEATURES*8-1:0]       feature_vector_i,
    input  wire [NUM_INTERNAL*3-1:0]       node_feature_i,
    input  wire [NUM_INTERNAL*8-1:0]       node_threshold_i,
    input  wire [NUM_INTERNAL*4-1:0]       node_left_i,
    input  wire [NUM_INTERNAL*4-1:0]       node_right_i,
    input  wire [NUM_LEAVES*8-1:0]         leaf_value_i,
    output reg                             busy_o,
    output reg                             pred_valid_o,
    output reg  [7:0]                      pred_value_o,
    output reg                             error_o
);

  localparam [1:0] S_IDLE = 2'd0;
  localparam [1:0] S_STEP = 2'd1;

  reg [1:0] state_q;
  reg [1:0] depth_q;
  reg [2:0] current_node_q;

  reg [2:0] node_feature_sel;
  reg [7:0] node_threshold_sel;
  reg [3:0] node_left_sel;
  reg [3:0] node_right_sel;
  reg [7:0] feature_value_sel;
  reg [3:0] next_child_sel;

  always @(*) begin
    node_feature_sel   = 3'd0;
    node_threshold_sel = 8'd0;
    node_left_sel      = 4'd0;
    node_right_sel     = 4'd0;
    feature_value_sel  = 8'd0;
    next_child_sel     = 4'd0;

    node_feature_sel   = node_feature_i[(current_node_q*3) +: 3];
    node_threshold_sel = node_threshold_i[(current_node_q*8) +: 8];
    node_left_sel      = node_left_i[(current_node_q*4) +: 4];
    node_right_sel     = node_right_i[(current_node_q*4) +: 4];
    feature_value_sel  = feature_vector_i[(node_feature_sel*8) +: 8];
    next_child_sel     = (feature_value_sel <= node_threshold_sel) ? node_left_sel : node_right_sel;
  end

  always @(posedge clk) begin
    if (~rst_n || clear_i) begin
      state_q         <= S_IDLE;
      depth_q         <= 2'd0;
      current_node_q  <= 3'd0;
      busy_o          <= 1'b0;
      pred_valid_o    <= 1'b0;
      pred_value_o    <= 8'd0;
      error_o         <= 1'b0;
    end else begin
      pred_valid_o <= 1'b0;

      case (state_q)
        S_IDLE: begin
          busy_o <= 1'b0;
          if (run_i) begin
            if (model_loaded_i && features_loaded_i) begin
              state_q        <= S_STEP;
              depth_q        <= 2'd0;
              current_node_q <= 3'd0;
              busy_o         <= 1'b1;
              error_o        <= 1'b0;
            end else begin
              error_o <= 1'b1;
            end
          end
        end

        S_STEP: begin
          if (depth_q == 2'd2) begin
            state_q <= S_IDLE;
            busy_o  <= 1'b0;
            pred_valid_o <= 1'b1;

            /* verilator lint_off WIDTHEXPAND */
            if ((next_child_sel >= LEAF_BASE) && (next_child_sel < (LEAF_BASE + NUM_LEAVES))) begin
              pred_value_o <= leaf_value_i[((next_child_sel - LEAF_BASE)*8) +: 8];
            /* verilator lint_on WIDTHEXPAND */
              error_o      <= 1'b0;
            end else begin
              pred_value_o <= 8'd0;
              error_o      <= 1'b1;
            end
          end else begin
            /* verilator lint_off WIDTHEXPAND */
            if (next_child_sel < NUM_INTERNAL) begin
            /* verilator lint_on WIDTHEXPAND */
              current_node_q <= next_child_sel[2:0];
              depth_q        <= depth_q + 2'd1;
            end else begin
              state_q      <= S_IDLE;
              busy_o       <= 1'b0;
              pred_valid_o <= 1'b1;
              pred_value_o <= 8'd0;
              error_o      <= 1'b1;
            end
          end
        end

        default: begin
          state_q <= S_IDLE;
          busy_o  <= 1'b0;
          error_o <= 1'b1;
        end
      endcase
    end
  end

endmodule
