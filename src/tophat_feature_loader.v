/*
 * Copyright (c) 2026 Patrick Farley
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tophat_feature_loader #(
    parameter integer NUM_FEATURES = 8
) (
    input  wire                           clk,
    input  wire                           rst_n,
    input  wire                           clear_i,
    input  wire                           consume_i,
    input  wire                           feature_byte_valid_i,
    input  wire [7:0]                     feature_byte_i,
    output reg                            features_loaded_o,
    output reg [NUM_FEATURES*8-1:0]       feature_vector_o
);

  localparam integer FEATURE_IDX_W = 4;
  reg [FEATURE_IDX_W-1:0] feature_idx_q;

  always @(posedge clk) begin
    if (~rst_n || clear_i) begin
      feature_idx_q      <= {FEATURE_IDX_W{1'b0}};
      features_loaded_o  <= 1'b0;
      feature_vector_o   <= {(NUM_FEATURES*8){1'b0}};
    end else begin
      if (consume_i) begin
        features_loaded_o <= 1'b0;
      end

      if (feature_byte_valid_i) begin
        if (feature_idx_q == {FEATURE_IDX_W{1'b0}}) begin
          features_loaded_o <= 1'b0;
        end

        feature_vector_o[(feature_idx_q*8) +: 8] <= feature_byte_i;

        if (feature_idx_q == (NUM_FEATURES - 1)) begin
          feature_idx_q     <= {FEATURE_IDX_W{1'b0}};
          features_loaded_o <= 1'b1;
        end else begin
          feature_idx_q <= feature_idx_q + {{(FEATURE_IDX_W-1){1'b0}}, 1'b1};
        end
      end
    end
  end

endmodule

