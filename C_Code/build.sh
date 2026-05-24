#!/bin/bash

riscv32-unknown-elf-gcc -std=gnu99 -mabi=ilp32 -march=rv32i -nostartfiles -Os -static \
-specs=nano.specs -Wl,-Tsections.lds -Wl,-Map=output.map -Wall -Werror -Wconversion \
-Wsign-conversion -Wextra -flto -fstack-usage -ffunction-sections -fdata-sections \
-o a.elf start.s \
main.c \
core_library/io.c \
core_library/slice.c \
core_library/utility.c \
core_library/dispatching.c \
core_library/coroutines.c \
command_wrappers.c

riscv32-unknown-elf-objcopy -O binary a.elf a.out

python3 convert_bin_init.py -RV32
