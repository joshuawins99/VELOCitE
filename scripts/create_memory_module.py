#!/usr/bin/env python3
import os
import argparse

def split_into_hex_files(mem_data, base_dir, words):
    mem1 = []
    mem2 = []
    mem3 = []
    mem4 = []

    # Split each 32-bit word into 4 bytes
    for line in mem_data:
        word = line.strip().zfill(8)
        mem4.append(word[0:2])
        mem3.append(word[2:4])
        mem2.append(word[4:6])
        mem1.append(word[6:8])

    # Pad to WORDS with zeros
    while len(mem1) < words:
        mem1.append("00")
        mem2.append("00")
        mem3.append("00")
        mem4.append("00")

    # Write files
    paths = {}
    for name, data in [
        ("mem1.mem", mem1),
        ("mem2.mem", mem2),
        ("mem3.mem", mem3),
        ("mem4.mem", mem4),
    ]:
        full = os.path.join(base_dir, name)
        with open(full, "w") as f:
            f.write("\n".join(data))
        paths[name] = os.path.abspath(full)

    return paths

def generate_verilog_integrated(mem_file, output_file, words=256, offset=0, prefill=1):
    with open(mem_file, 'r') as f:
        mem_data = [line.strip() for line in f.readlines()]

    num_entries = len(mem_data)

    verilog_code = f"""module picosoc_mem #(
    parameter address_width = 16,
    parameter integer WORDS = {words},
    parameter integer OFFSET = {offset},
    parameter integer PREFILL = {prefill}
) (
    input clk,
    input [3:0] wen,
    input [address_width-1:0] addr,
    input [31:0] wdata,
    output reg [31:0] rdata
);

    // Memory array declaration
    reg [7:0] mem1 [0:WORDS-1];
    reg [7:0] mem2 [0:WORDS-1];
    reg [7:0] mem3 [0:WORDS-1];
    reg [7:0] mem4 [0:WORDS-1];

    initial begin
    `ifdef SIM
        mem1 = '{{default:0}};
        mem2 = '{{default:0}};
        mem3 = '{{default:0}};
        mem4 = '{{default:0}};
    `else
"""
    
    for idx in range(len(mem_data)):
        verilog_code += f"        mem1[OFFSET + {idx}] = 0;\n"
        verilog_code += f"        mem2[OFFSET + {idx}] = 0;\n"
        verilog_code += f"        mem3[OFFSET + {idx}] = 0;\n"
        verilog_code += f"        mem4[OFFSET + {idx}] = 0;\n"

    verilog_code += "   `endif\n"
    verilog_code += "   if (PREFILL) begin\n"

    # Embed initialization statements within the initial block
    for idx, line in enumerate(mem_data):
        verilog_code += f"            mem1[OFFSET + {idx}] = 8'h{line[-2:]};\n"
        verilog_code += f"            mem2[OFFSET + {idx}] = 8'h{line[-4:-2]};\n"
        verilog_code += f"            mem3[OFFSET + {idx}] = 8'h{line[-6:-4]};\n"
        verilog_code += f"            mem4[OFFSET + {idx}] = 8'h{line[-8:-6]};\n"

    # Fill remaining entries with zero
    for idx in range(num_entries, words):
        verilog_code += f"            mem1[OFFSET + {idx}] = 8'h00;\n"
        verilog_code += f"            mem2[OFFSET + {idx}] = 8'h00;\n"
        verilog_code += f"            mem3[OFFSET + {idx}] = 8'h00;\n"
        verilog_code += f"            mem4[OFFSET + {idx}] = 8'h00;\n"

    verilog_code += """        end
    end

    always @(posedge clk) begin
        rdata <= {mem4[addr], mem3[addr], mem2[addr], mem1[addr]};
    end

    always @(posedge clk) begin
        if (wen[0]) mem1[addr] <= wdata[ 7: 0];
        if (wen[1]) mem2[addr] <= wdata[15: 8];
        if (wen[2]) mem3[addr] <= wdata[23:16];
        if (wen[3]) mem4[addr] <= wdata[31:24];
    end
endmodule
"""

    with open(output_file, 'w') as f:
        f.write(verilog_code)

def generate_verilog_mem_files(mem_file, output_file, words=256, offset=0, prefill=1):
    with open(mem_file, 'r') as f:
        mem_data = [line.strip() for line in f.readlines()]

    out_dir = os.path.abspath(os.path.dirname(mem_file))

    # Generate hex files and get absolute paths
    hex_paths = split_into_hex_files(mem_data, out_dir, words)

    verilog_code = f"""module picosoc_mem #(
    parameter address_width = 16,
    parameter integer WORDS = {words},
    parameter integer OFFSET = {offset},
    parameter integer PREFILL = {prefill}
) (
    input clk,
    input [3:0] wen,
    input [address_width-1:0] addr,
    input [31:0] wdata,
    output reg [31:0] rdata
);

    reg [7:0] mem1 [0:WORDS-1];
    reg [7:0] mem2 [0:WORDS-1];
    reg [7:0] mem3 [0:WORDS-1];
    reg [7:0] mem4 [0:WORDS-1];

    initial begin
`ifdef SIM
        mem1 = '{{default:0}};
        mem2 = '{{default:0}};
        mem3 = '{{default:0}};
        mem4 = '{{default:0}};
`endif

        if (PREFILL) begin
            $readmemh("{hex_paths['mem1.mem']}", mem1, OFFSET);
            $readmemh("{hex_paths['mem2.mem']}", mem2, OFFSET);
            $readmemh("{hex_paths['mem3.mem']}", mem3, OFFSET);
            $readmemh("{hex_paths['mem4.mem']}", mem4, OFFSET);
        end
    end

    always @(posedge clk) begin
        rdata <= {{mem4[addr], mem3[addr], mem2[addr], mem1[addr]}};
    end

    always @(posedge clk) begin
        if (wen[0]) mem1[addr] <= wdata[ 7: 0];
        if (wen[1]) mem2[addr] <= wdata[15: 8];
        if (wen[2]) mem3[addr] <= wdata[23:16];
        if (wen[3]) mem4[addr] <= wdata[31:24];
    end
endmodule
"""

    with open(output_file, 'w') as f:
        f.write(verilog_code)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="create_memory_module.py", description="Create Memory Module", add_help=False,
                                     formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=50))
    parser.add_argument("--help", action="help", help="Show this help message and exit")
    parser.add_argument("--input-mem", help="Input .mem file path")
    parser.add_argument("--output-v", help="Output .v file path")
    parser.add_argument("--integrated", action='store_true', help="Select between mem file data integration or use readmemh")
    parser.add_argument("--prefill", help="Prefill option. Default is 1", default=1)
    parser.add_argument("--offset", help="Offset for start of load. Default is 0", default=0)

    args = parser.parse_args()

    offset = int(args.offset)
    prefill = int(args.prefill)
    if (args.integrated):
        generate_verilog_integrated(args.input_mem, args.output_v, offset=offset, prefill=prefill)
    else:
        generate_verilog_mem_files(args.input_mem, args.output_v, offset=offset, prefill=prefill)
