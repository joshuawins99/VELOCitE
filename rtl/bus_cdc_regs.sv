/*@ModuleMetadataBegin
Name : Bus CDC Regs
Description : Module data CDC and busy CPU router registers
Reg0 :
    Name : Busy Timeout
    Description : Timeout in clock ticks before an asserted busy is ignored (Defaults to 0 or disabled)
    Permissions : Read/Write
Reg1 :
    Name : Number of Bitmap Reads
    Description : Read the number of reads of the Stuck Module Bitmap register to get the entire bitmap
    Permissions : Read
Reg2 :
    Name : Stuck Module Bitmap
    Description : Read the bitmap of the modules currently stuck. Each read will read the next \
                  chunk of the bitmap up to the Number of Bitmap Reads register and then cycle back to the start.
    Permissions : Read
Reg3 :
    Name : Reset Module Index
    Description : Write enumeration index number to reset module
    Permissions : Write
@ModuleMetadataEnd*/
module bus_cdc_regs
import cpu_reg_package::*;
#(
    parameter BaseAddress     = 0,
    parameter address_width   = 16,
    parameter data_width      = 8,
    parameter Address_Wording = 1
)(
    input  logic                     clk_i,
    input  logic                     reset_i,
    input  logic [address_width-1:0] address_i,
    input  logic [data_width-1:0]    data_i,
    output logic [data_width-1:0]    data_o,
    input  logic                     rd_wr_i,
    input  logic [num_entries-1:0]   busy_bits_i,
    output logic [num_entries-1:0]   busy_enable_o,
    output logic [num_entries-1:0]   busy_reset_module_o
);

    localparam Busy_Timeout_Address           = BaseAddress + (0*Address_Wording);
    localparam Number_of_Bitmap_Reads_Address = BaseAddress + (1*Address_Wording);
    localparam Stuck_Module_Bitmap_Address    = BaseAddress + (2*Address_Wording);
    localparam Reset_Module_Index_Address     = BaseAddress + (3*Address_Wording);

    localparam Num_Stuck_Module_Index_Reads   = (num_entries + data_width - 1) / data_width;

    logic [num_entries-1:0]                          busy_reset_module;
    logic [num_entries-1:0]                          busy_enable;
    logic [num_entries-1:0]                          timed_out_modules;
    logic [31:0]                                     busy_timeout;
    logic [31:0]                                     busy_timeout_counter [num_entries];
    logic                                            update_busy_timeout;
    logic [$clog2(Num_Stuck_Module_Index_Reads)-1:0] current_read_busy_slice;

    function logic [num_entries-1:0] num_to_bit_pos (
        input logic [31:0] num
    );
        logic [num_entries-1:0] result;

        result = '0;

        if (num < num_entries) begin
            result[num] = 1'b1;
        end

        return result;
    endfunction

    //------------------------------------------------------------
    // Per-module timeout logic
    //------------------------------------------------------------
    genvar idx;
    generate
        for (idx = 0; idx < num_entries; idx++) begin : gen_busy_timeout
            always_ff @(posedge clk_i) begin
                if (reset_i == 1'b1) begin
                    busy_timeout_counter[idx] <= '0;
                    busy_enable[idx]          <= 1'b1;
                    timed_out_modules[idx]    <= 1'b0;
                end else begin
                    //------------------------------------------------
                    // Manual module reset from CPU
                    //------------------------------------------------
                    if (busy_reset_module[idx] == 1'b1) begin
                        busy_enable[idx]       <= 1'b1;
                        timed_out_modules[idx] <= 1'b0;
                        busy_timeout_counter[idx] <= busy_timeout;
                    end

                    //------------------------------------------------
                    // Global timeout value changed
                    //------------------------------------------------
                    else if (update_busy_timeout == 1'b1) begin
                        busy_timeout_counter[idx] <= busy_timeout;
                    end

                    //------------------------------------------------
                    // Timeout disabled
                    //------------------------------------------------
                    else if (busy_timeout == 0) begin
                        busy_enable[idx]       <= 1'b1;
                        timed_out_modules[idx] <= 1'b0;
                    end

                    //------------------------------------------------
                    // Not busy
                    //------------------------------------------------
                    else if (busy_bits_i[idx] == 1'b0) begin
                        busy_timeout_counter[idx] <= busy_timeout;

                        // Auto recover once busy clears
                        busy_enable[idx]       <= 1'b1;
                        timed_out_modules[idx] <= 1'b0;
                    end

                    //------------------------------------------------
                    // Busy and timer active
                    //------------------------------------------------
                    else if (busy_timeout_counter[idx] > 1) begin
                        busy_timeout_counter[idx] <= busy_timeout_counter[idx] - 1'b1;
                    end

                    //------------------------------------------------
                    // Timed out
                    //------------------------------------------------
                    else begin
                        busy_enable[idx]       <= 1'b0;
                        timed_out_modules[idx] <= 1'b1;
                    end
                end
            end
        end
    endgenerate

    //------------------------------------------------------------
    // Data Reads
    //------------------------------------------------------------
    always_ff @(posedge clk_i) begin
        if (reset_i == 1'b1) begin
            data_o <= '0;
            current_read_busy_slice <= '0;
        end else begin
            if (rd_wr_i == 1'b0) begin
                unique case (address_i)
                    Busy_Timeout_Address : begin
                        data_o <= busy_timeout;
                    end
                    Number_of_Bitmap_Reads_Address : begin
                        data_o <= Num_Stuck_Module_Index_Reads;
                        current_read_busy_slice <= '0;
                    end
                    Stuck_Module_Bitmap_Address : begin
                        data_o <= timed_out_modules[current_read_busy_slice*data_width +: data_width];
                        if (current_read_busy_slice < (Num_Stuck_Module_Index_Reads - 1)) begin
                            current_read_busy_slice <= current_read_busy_slice + 1'b1;
                        end else begin
                            current_read_busy_slice <= '0;
                        end
                    end
                    default : begin
                        data_o <= '0;
                    end
                endcase
            end
        end
    end

    //------------------------------------------------------------
    // Data Writes
    //------------------------------------------------------------
    always_ff @(posedge clk_i) begin
        update_busy_timeout <= 1'b0;
        busy_reset_module   <= '0;

        if (reset_i == 1'b1) begin
            busy_timeout      <= '0;
            busy_reset_module <= '0;
        end else begin
            if (rd_wr_i == 1'b1) begin
                unique case (address_i)
                    Busy_Timeout_Address : begin
                        busy_timeout        <= data_i;
                        update_busy_timeout <= 1'b1;
                    end
                    Reset_Module_Index_Address : begin
                        busy_reset_module <= num_to_bit_pos(data_i);
                    end
                    default : begin
                    end
                endcase
            end
        end
    end

    assign busy_reset_module_o = busy_reset_module;
    assign busy_enable_o       = busy_enable;

endmodule