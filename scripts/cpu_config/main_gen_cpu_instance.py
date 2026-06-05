#!/usr/bin/env python3
import os
import subprocess
import shutil
import argparse
from cpu_config_parser import *
from verilog import *
from registers import *
from register_docs import *

current_directory = os.path.abspath(__file__)

from headers.c_headers import export_c_headers
from headers.python_headers import export_python_headers
from headers.zig_headers import export_zig_headers
from headers.verilog_headers import export_verilog_headers

config_file_names = ["cpu_config.txt", "cpu_config.cfg"]

directory_path = "."
build_script = "build_single_module.sh"
reference_system_file = "ref_fpga_sys_lite.sv"

try: #Test for existance of velocite_version. If not, then assume submodule use
    velocite_version # type: ignore
except:
    velocite_version_file_path = os.path.normpath(f"{go_up_n_levels(current_directory, 3)}/version")
    with open(velocite_version_file_path, 'r') as file:
        velocite_version = file.readline()

GEN_HEADER_FLAGS = {
    "python": "python_header",
    "c": "c_header",
    "strip-verilog": "strip_verilog",
    "new-python": "new_python_header",
    "new-c": "new_c_header",
    "zig": "zig_header",
    "verilog-muxes": "verilog_muxes",
    "verilog-regs": "verilog_regs",
    "use-verilog-module-names": "verilog_module_names",
    "verilog-files-per-module": "verilog_files_per_module",
}

parser = argparse.ArgumentParser(prog="generate_cpu_instance.py", description=f"Generate CPU Instance (VELOCitE v{velocite_version})", add_help=False,
                                 formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, max_help_position=50))
parser.add_argument("--help", action="help", help="Show this help message and exit")
parser.add_argument("--version", action="version", help="Show version and exit", version=f"Generate CPU Instance (VELOCitE v{velocite_version})")
parser.add_argument("--build", action='store_true', help="Build CPU Code and create combined output sv")
parser.add_argument("--configs-path", help="Specify config directories path")
parser.add_argument("--output-path", help="Specify output path for generated files")
parser.add_argument("--gen-headers", nargs="*", choices=list(GEN_HEADER_FLAGS.keys()), metavar="LANG", default=argparse.SUPPRESS,
                    help="Generate/Configure header files. Options are:\n  " + "\n  ".join(list(GEN_HEADER_FLAGS.keys())))
parser.add_argument("--print-all-registers", action='store_true', help="Prints all registers to console")
parser.add_argument("--print-user-registers", action='store_true', help="Prints user registers to console")
parser.add_argument("--save-all-registers", action='store_true', help="Saves all registers to a cpu_registers.txt file")
parser.add_argument("--save-user-registers", action='store_true', help="Saves user registers to a cpu_registers.txt file")
parser.add_argument("--save-all-registers-html", nargs="?", choices = ["dark", "light"], const = "dark", default = "", help="Saves all registers to a cpu_registers.html file")
parser.add_argument("--save-user-registers-html", nargs="?", choices = ["dark", "light"], const = "dark", default = "", help="Saves user registers to a cpu_registers.html file")

args = parser.parse_args()

if args.configs_path:
    directory_path = args.configs_path

absolute_path = os.path.abspath(directory_path)
absolute_output_path = absolute_path

if args.output_path:
    absolute_output_path = os.path.abspath(args.output_path)
    os.makedirs(f"{absolute_output_path}", exist_ok=True)

#folders = list_folders(directory_path)
#print(folders)

config_files = check_config_files(absolute_path, config_file_names)
#print(config_files)
if not any(config_files.values()):
    raise FileNotFoundError("No Config Files Found")

filtered_dirs = [dir_name for dir_name in config_files if config_files.get(dir_name)]
#print(filtered_dirs)

parsed_configs, submodule_reg_map = process_configs(absolute_path, config_file_names)
#print(parsed_configs)
assign_auto_addresses(parsed_configs, submodule_reg_map)
#print(parsed_configs)

if args.print_all_registers:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, submodule_reg_map, absolute_output_path, user_modules_only=False)

if args.save_all_registers:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, submodule_reg_map, absolute_output_path, user_modules_only=False, 
                                        save_to_file=True, print_to_console=False)

if args.print_user_registers:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, submodule_reg_map, absolute_output_path, user_modules_only=True)

if args.save_user_registers:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, submodule_reg_map, absolute_output_path, user_modules_only=True, 
                                        save_to_file=True, print_to_console=True)
        
if args.save_user_registers_html:
    if (filtered_dirs):
        if (args.save_all_registers_html == "light"):
            dark_mode = False
        else:
            dark_mode = True
        dump_all_registers_html(parsed_configs, submodule_reg_map, absolute_output_path, user_modules_only=True, 
                                save_to_file=True, print_to_console=False, dark_mode=dark_mode)
        
if args.save_all_registers_html:
    if (filtered_dirs):
        if (args.save_all_registers_html == "light"):
            dark_mode = False
        else:
            dark_mode = True
        dump_all_registers_html(parsed_configs, submodule_reg_map, absolute_output_path, user_modules_only=False, 
                                save_to_file=True, print_to_console=False, dark_mode=dark_mode)

header_flags = {flag: False for flag in GEN_HEADER_FLAGS.values()}

try: #Check for args.gen_headers
    if not args.gen_headers: # type: ignore #Set default options if nothing is given
        args.gen_headers = ["c", "python"]

    if args.gen_headers:            
        for header in args.gen_headers:
            if header not in GEN_HEADER_FLAGS:
                raise SyntaxError(f"'{header}' is not a valid header option")

            header_flags[GEN_HEADER_FLAGS[header]] = True
        
        if (filtered_dirs):
            if (header_flags["python_header"] or header_flags["new_python_header"]):
                export_python_headers(parsed_configs=parsed_configs, submodule_reg_map=submodule_reg_map, 
                                      directory_path=absolute_output_path, reg_width_bytes=4, user_modules_only=False, 
                                      new_python_header=header_flags["new_python_header"])
            if (header_flags["c_header"] or header_flags["new_c_header"]):
                export_c_headers(parsed_configs=parsed_configs, submodule_reg_map=submodule_reg_map, 
                                 directory_path=absolute_output_path, reg_width_bytes=4, user_modules_only=False, new_c_header=header_flags["new_c_header"])
            
            if header_flags["zig_header"]:
                export_zig_headers(parsed_configs=parsed_configs, submodule_reg_map=submodule_reg_map, directory_path=absolute_output_path, 
                                   reg_width_bytes=4, user_modules_only=False)
            if header_flags["verilog_muxes"] or header_flags["verilog_regs"]:
                export_verilog_headers(parsed_configs=parsed_configs, submodule_reg_map=submodule_reg_map, directory_path=absolute_output_path, 
                                       reg_width_bytes=4, user_modules_only=False, verilog_muxes=header_flags["verilog_muxes"], 
                                       verilog_regs=header_flags["verilog_regs"], strip_verilog=header_flags["strip_verilog"], 
                                       verilog_module_names=header_flags["verilog_module_names"], file_per_module=header_flags["verilog_files_per_module"])
except:
    pass

code_folders = get_code_folders(parsed_configs)
#print(code_folders)

default_c_code_path = "C_Code"  #Default Folder

if args.build:
    if os.path.exists(f"{go_up_n_levels(current_directory,3)}/{build_script}"):
        default_c_code_path = os.path.join(current_directory,go_up_n_levels(current_directory,3),default_c_code_path)
        if (filtered_dirs):
            for cpu_name in filtered_dirs:
                config_folder = code_folders.get(cpu_name)
                build_folder = (
                    os.path.join(absolute_path, cpu_name, config_folder)
                    if config_folder
                    else default_c_code_path
                )
                build_folder = os.path.abspath(build_folder)
                parent_directory = go_up_n_levels(current_directory,3)
                print(f"Running build for '{cpu_name}' using Code folder: {build_folder}\n")
                try:
                    if args.gen_headers:
                        if (build_folder != default_c_code_path): 
                            if os.path.exists(f"{build_folder}/{cpu_name}_registers.h"):
                                os.remove(f"{build_folder}/{cpu_name}_registers.h")
                            print(f"Moved generated header: {absolute_output_path}/{cpu_name}/{cpu_name}_registers.h -> {build_folder}\n")
                            shutil.move(f"{absolute_output_path}/{cpu_name}/{cpu_name}_registers.h", build_folder)
                            if header_flags["zig_header"]:
                                if os.path.exists(f"{build_folder}/{cpu_name}_registers.zig"):
                                    os.remove(f"{build_folder}/{cpu_name}_registers.zig")
                                print(f"Moved generated header: {absolute_output_path}/{cpu_name}/{cpu_name}_registers.zig -> {build_folder}\n")
                                shutil.move(f"{absolute_output_path}/{cpu_name}/{cpu_name}_registers.zig", build_folder)
                    result = subprocess.run(["bash", f"{build_script}", "--code-folder", build_folder, "--gen-cpu-inst-name", cpu_name], cwd=parent_directory, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(result.stderr)
                        raise subprocess.CalledProcessError(returncode=result.returncode, cmd=" ".join(result.args))
                    else:
                        print(result.stdout + result.stderr) 
                except FileNotFoundError:
                    raise FileNotFoundError (f"Build folder not found for {cpu_name}: {build_folder}")

                curr_config_dict = {cpu_name: parsed_configs.get(cpu_name)}
                save_systemverilog_files(curr_config_dict, submodule_reg_map, absolute_output_path)
                update_cpu_modules_file(curr_config_dict, absolute_output_path, reference_file=f"{parent_directory}/{reference_system_file}")
                #subprocess.run(["bash", "-c", "git clean -fdx"], cwd=parent_directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        raise FileNotFoundError(f"{go_up_n_levels(current_directory,3)}/{build_script} not found. Are you using the source repo?")

else:
    if os.path.exists(f"{go_up_n_levels(current_directory,1)}/{reference_system_file}"):
        if (filtered_dirs):
            save_systemverilog_files(parsed_configs, submodule_reg_map, absolute_output_path)
            update_cpu_modules_file(parsed_configs, absolute_output_path, reference_file=reference_system_file)
    else:
        raise FileNotFoundError(f"{go_up_n_levels(current_directory,1)}/{reference_system_file} not found. Are you using a release build?")


#systemverilog_output = generate_systemverilog(parsed_configs)
#print(systemverilog_output)
