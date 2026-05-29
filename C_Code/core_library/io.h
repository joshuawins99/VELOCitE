#ifndef IO_H
#define IO_H

#include "slice.h"
#include "utility.h"
#include "fpga_cpu.h"

#define WriteIO(addr,val)   (*(volatile uint8_t*) (addr) = (val))
#define WriteIO32(addr,val) (*(volatile uint32_t*) (addr) = (val))
#define ReadIO(addr)        (*(volatile uint8_t*) (addr))
#define ReadIO32(addr)      (*(volatile uint32_t*) (addr))

char get_char (void);
void put_char (uint8_t);
void Print (uint8_t, const char *);
void PrintSlice (uint8_t, const SliceU8);
SliceU8 ReadVersion (void);
SliceU8 readFPGA (uint32_t);
void writeFPGA (uint32_t, uint32_t);

#endif