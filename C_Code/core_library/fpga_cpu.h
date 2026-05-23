#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>

#define ADDR_WORD 4 //Byte Addressed 32bit CPU

#define Version_String_BaseAddress 0x8000
#define IO_CPU_BaseAddress         0x9000
#define UART_CPU_BaseAddress       0x9100

#define VersionStringSize 64

#define MAX_CMD_ARGS 3 // Command + arguments
#define MAX_TOKEN_LENGTH 16

#define TOKENIZER_SEPARATOR ','

//#define REPL_UART //Change from default mode to REPL mode
//#define CARRIAGE_RETURN //Add a \r in addition to \n for a newline