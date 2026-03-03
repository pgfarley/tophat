/*
 * Copyright (c) 2026 Patrick Farley
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tophat_tree_core #(
    parameter integer NUM_FEATURES = 8,
    parameter integer FEATURE_IDX_W = 3,
    parameter integer TREE_DEPTH = 3,
    parameter integer NUM_INTERNAL = ((1 << TREE_DEPTH) - 1),
    parameter integer NUM_LEAVES = (1 << TREE_DEPTH)
) (
    input  wire                            clk,
    input  wire                            rst_n,
    input  wire                            clear_i,
    input  wire                            run_i,
    input  wire                            model_loaded_i,
    input  wire                            features_loaded_i,
    input  wire [NUM_FEATURES*8-1:0]       feature_vector_i,
    input  wire [NUM_INTERNAL*FEATURE_IDX_W-1:0] node_feature_i,
    input  wire [NUM_INTERNAL*8-1:0]       node_threshold_i,
    input  wire [NUM_LEAVES*8-1:0]         leaf_value_i,
    output reg                             busy_o,
    output reg                             pred_valid_o,
    output reg  [7:0]                      pred_value_o,
    output reg                             error_o
);

  localparam [1:0] S_IDLE = 2'd0;
  localparam [1:0] S_STEP = 2'd1;
  localparam integer DEPTH_W = (TREE_DEPTH <= 1) ? 1 : $clog2(TREE_DEPTH);
  localparam integer NODE_IDX_W = (NUM_INTERNAL <= 1) ? 1 : $clog2(NUM_INTERNAL);
  localparam integer FULL_IDX_W = ((NUM_INTERNAL + NUM_LEAVES) <= 1) ? 1 : $clog2(NUM_INTERNAL + NUM_LEAVES);

  reg [1:0] state_q;
  reg [DEPTH_W-1:0] depth_q;
  reg [NODE_IDX_W-1:0] current_node_q;

  reg [FEATURE_IDX_W-1:0] node_feature_sel;
  reg [7:0] node_threshold_sel;
  reg [7:0] feature_value_sel;
  reg       branch_right_sel;
  reg [FULL_IDX_W-1:0] next_child_sel;
  reg [FULL_IDX_W-1:0] leaf_idx_sel;

  always @(*) begin
    node_feature_sel   = {FEATURE_IDX_W{1'b0}};
    node_threshold_sel = 8'd0;
    feature_value_sel  = 8'd0;
    branch_right_sel   = 1'b0;
    next_child_sel     = {FULL_IDX_W{1'b0}};
    leaf_idx_sel       = {FULL_IDX_W{1'b0}};

    node_feature_sel   = node_feature_i[(current_node_q*FEATURE_IDX_W) +: FEATURE_IDX_W];
    node_threshold_sel = node_threshold_i[(current_node_q*8) +: 8];
    feature_value_sel  = feature_vector_i[(node_feature_sel*8) +: 8];
    branch_right_sel   = (feature_value_sel <= node_threshold_sel) ? 1'b0 : 1'b1;
    next_child_sel     = ({1'b0, current_node_q} << 1) + {{(FULL_IDX_W-1){1'b0}}, 1'b1} + {{(FULL_IDX_W-1){1'b0}}, branch_right_sel};
    leaf_idx_sel       = next_child_sel - NUM_INTERNAL;
  end

  always @(posedge clk) begin
    if (~rst_n || clear_i) begin
      state_q         <= S_IDLE;
      depth_q         <= {DEPTH_W{1'b0}};
      current_node_q  <= {NODE_IDX_W{1'b0}};
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
              depth_q        <= {DEPTH_W{1'b0}};
              current_node_q <= {NODE_IDX_W{1'b0}};
              busy_o         <= 1'b1;
              error_o        <= 1'b0;
            end else begin
              error_o <= 1'b1;
            end
          end
        end

        S_STEP: begin
          if (depth_q == (TREE_DEPTH - 1)) begin
            state_q <= S_IDLE;
            busy_o  <= 1'b0;
            pred_valid_o <= 1'b1;
            pred_value_o <= leaf_value_i[(leaf_idx_sel*8) +: 8];
            error_o      <= 1'b0;
          end else begin
            current_node_q <= next_child_sel[NODE_IDX_W-1:0];
            depth_q        <= depth_q + {{(DEPTH_W-1){1'b0}}, 1'b1};
          end
        end

        default: begin
          state_q <= S_IDLE;
          busy_o  <= 1'b0;
          error_o <= 1'b0;
        end
      endcase
    end
  end

endmodule
