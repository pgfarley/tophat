/*
 * Copyright (c) 2026 Patrick Farley
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_pgfarley_tophat_top (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // Input protocol:
  // - ui_in[7:0]  : payload byte
  // - uio_in[0]   : valid
  // - uio_in[2:1] : command
  //   2'b00 -> model byte stream
  //   2'b01 -> feature byte stream
  //   2'b10 -> control byte (bit0=run, bit1=clear)
  //
  // Output status on uio_out:
  // - uio_out[3] ready
  // - uio_out[4] busy
  // - uio_out[5] pred_valid
  // - uio_out[6] model_loaded
  // - uio_out[7] error_or_missing_features

  wire model_byte_valid;
  wire [7:0] model_byte;
  wire feature_byte_valid;
  wire [7:0] feature_byte;
  wire run_cmd;
  wire clear_cmd;

  wire model_loaded;
  wire features_loaded;

  wire [20:0] node_feature_flat;
  wire [55:0] node_threshold_flat;
  wire [27:0] node_left_flat;
  wire [27:0] node_right_flat;
  wire [63:0] leaf_value_flat;
  wire [63:0] feature_vector_flat;

  wire core_busy;
  wire pred_valid;
  wire [7:0] pred_value;
  wire core_error;

  wire [7:0] result_uo_out;
  wire [7:0] result_uio_out;
  wire [7:0] result_uio_oe;

  wire io_ready;
  assign io_ready = ~core_busy;

  tophat_io_intf u_io_intf (
      .clk(clk),
      .rst_n(rst_n),
      .ena_i(ena),
      .io_ready_i(io_ready),
      .data_i(ui_in),
      .valid_i(uio_in[0]),
      .cmd_i(uio_in[2:1]),
      .model_byte_valid_o(model_byte_valid),
      .model_byte_o(model_byte),
      .feature_byte_valid_o(feature_byte_valid),
      .feature_byte_o(feature_byte),
      .run_o(run_cmd),
      .clear_o(clear_cmd)
  );

  tophat_model_loader #(
      .NUM_INTERNAL(7),
      .NUM_LEAVES(8)
  ) u_model_loader (
      .clk(clk),
      .rst_n(rst_n),
      .clear_i(clear_cmd),
      .model_byte_valid_i(model_byte_valid),
      .model_byte_i(model_byte),
      .model_loaded_o(model_loaded),
      .node_feature_o(node_feature_flat),
      .node_threshold_o(node_threshold_flat),
      .node_left_o(node_left_flat),
      .node_right_o(node_right_flat),
      .leaf_value_o(leaf_value_flat)
  );

  tophat_feature_loader #(
      .NUM_FEATURES(8)
  ) u_feature_loader (
      .clk(clk),
      .rst_n(rst_n),
      .clear_i(clear_cmd),
      .consume_i(run_cmd),
      .feature_byte_valid_i(feature_byte_valid),
      .feature_byte_i(feature_byte),
      .features_loaded_o(features_loaded),
      .feature_vector_o(feature_vector_flat)
  );

  tophat_tree_core #(
      .NUM_FEATURES(8),
      .NUM_INTERNAL(7),
      .NUM_LEAVES(8),
      .LEAF_BASE(7)
  ) u_tree_core (
      .clk(clk),
      .rst_n(rst_n),
      .clear_i(clear_cmd),
      .run_i(run_cmd),
      .model_loaded_i(model_loaded),
      .features_loaded_i(features_loaded),
      .feature_vector_i(feature_vector_flat),
      .node_feature_i(node_feature_flat),
      .node_threshold_i(node_threshold_flat),
      .node_left_i(node_left_flat),
      .node_right_i(node_right_flat),
      .leaf_value_i(leaf_value_flat),
      .busy_o(core_busy),
      .pred_valid_o(pred_valid),
      .pred_value_o(pred_value),
      .error_o(core_error)
  );

  tophat_result_if u_result_if (
      .pred_value_i(pred_value),
      .pred_valid_i(pred_valid),
      .busy_i(core_busy),
      .model_loaded_i(model_loaded),
      .features_loaded_i(features_loaded),
      .error_i(core_error),
      .uo_out_o(result_uo_out),
      .uio_out_o(result_uio_out),
      .uio_oe_o(result_uio_oe)
  );

  assign uo_out = result_uo_out;
  assign uio_out = result_uio_out;
  assign uio_oe = result_uio_oe;

  // List currently unused input bits to prevent warnings.
  wire _unused = &{uio_in[7:3], 1'b0};

endmodule
