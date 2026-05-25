#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdbool.h>

#ifndef ADDR_WORD
#define ADDR_WORD 4 //Byte Addressed 32bit CPU
#endif

#ifndef Version_String_BaseAddress
#define Version_String_BaseAddress 0x8000
#endif

#ifndef IO_CPU_BaseAddress
#define IO_CPU_BaseAddress         0x9000
#endif

#ifndef UART_CPU_BaseAddress
#define UART_CPU_BaseAddress       0x9100
#endif

#ifndef VersionStringSize
#define VersionStringSize 64
#endif

#ifndef MAX_CMD_ARGS
#define MAX_CMD_ARGS 3 // Command + arguments
#endif

#ifndef MAX_TOKEN_LENGTH
#define MAX_TOKEN_LENGTH 16
#endif

#ifndef MAX_CMD_QUEUE
#define MAX_CMD_QUEUE 32
#endif

#ifndef MAX_LINE_LENGTH
#define MAX_LINE_LENGTH 40
#endif

#ifndef TOKENIZER_SEPARATOR
#define TOKENIZER_SEPARATOR ','
#endif

// Coroutine Defines
#ifndef MAX_TASKS
#define MAX_TASKS 8
#endif

#ifndef FRAME_SIZE
#define FRAME_SIZE 64 // bytes per frame
#endif

//#define REPL_UART //Change from default mode to REPL mode
//#define CARRIAGE_RETURN //Add a \r in addition to \n for a newline