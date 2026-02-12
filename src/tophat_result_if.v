/*
 * Copyright (c) 2026 Patrick Farley
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tophat_result_if (
    input  wire [7:0] pred_value_i,
    input  wire       pred_valid_i,
    input  wire       busy_i,
    input  wire       model_loaded_i,
    input  wire       features_loaded_i,
    input  wire       error_i,
    output wire [7:0] uo_out_o,
    output wire [7:0] uio_out_o,
    output wire [7:0] uio_oe_o
);

  assign uo_out_o = pred_value_i;

  // uio[2:0] are inputs (valid/cmd).
  assign uio_out_o[0] = 1'b0;
  assign uio_out_o[1] = 1'b0;
  assign uio_out_o[2] = 1'b0;
  assign uio_out_o[3] = ~busy_i;           // ready
  assign uio_out_o[4] = busy_i;
  assign uio_out_o[5] = pred_valid_i;
  assign uio_out_o[6] = model_loaded_i;
  assign uio_out_o[7] = error_i | ~features_loaded_i;

  assign uio_oe_o = 8'b1111_1000;

endmodule
