/*
 * Copyright (c) 2026 Patrick Farley
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tophat_io_intf (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       ena_i,
    input  wire       io_ready_i,
    input  wire [7:0] data_i,
    input  wire       valid_i,
    input  wire [1:0] cmd_i,
    output reg        model_byte_valid_o,
    output reg  [7:0] model_byte_o,
    output reg        feature_byte_valid_o,
    output reg  [7:0] feature_byte_o,
    output reg        run_o,
    output reg        clear_o
);

  localparam [1:0] CMD_MODEL   = 2'b00;
  localparam [1:0] CMD_FEATURE = 2'b01;
  localparam [1:0] CMD_CTRL    = 2'b10;

  always @(posedge clk) begin
    model_byte_valid_o   <= 1'b0;
    feature_byte_valid_o <= 1'b0;
    run_o                <= 1'b0;
    clear_o              <= 1'b0;

    if (~rst_n) begin
      model_byte_o   <= 8'h00;
      feature_byte_o <= 8'h00;
    end else if (ena_i && io_ready_i && valid_i) begin
      case (cmd_i)
        CMD_MODEL: begin
          model_byte_valid_o <= 1'b1;
          model_byte_o       <= data_i;
        end
        CMD_FEATURE: begin
          feature_byte_valid_o <= 1'b1;
          feature_byte_o       <= data_i;
        end
        CMD_CTRL: begin
          run_o   <= data_i[0];
          clear_o <= data_i[1];
        end
        default: begin
          // Reserved command
        end
      endcase
    end
  end

endmodule

