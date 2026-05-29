#ifndef DISPATCHING_H
#define DISPATCHING_H

#include "slice.h"
#include "fpga_cpu.h"

typedef struct {
    char commands[MAX_CMD_QUEUE][MAX_LINE_LENGTH];
    slen_t slice_lengths[MAX_CMD_QUEUE];
    uint8_t head;
    uint8_t tail;
} CommandQueue;

typedef SliceU8 (*command_func)(SliceU8);

typedef struct {
    SliceU8 command;          // command name
    command_func func;        // function pointer
    uint8_t index;            // assigned at registration
    uint8_t is_coroutine;
} command_entry;

extern CommandQueue cmdQueue;
extern uint8_t queueMode;

uint8_t isQueueFull(void);
uint8_t isQueueEmpty(void);
void enqueueCommand(const SliceU8);
SliceU8 dequeueCommand(void);
void executeQueuedCommands(void);
void printQueuedCommands(void);
SliceU8 commandsList(SliceU8);
SliceU8 executeCommands(SliceU8);
void UARTCommand(SliceU8);
void ReadUART(void);
void setCommandsBuffer(command_entry *, uint8_t);
int8_t registerCommand(const char *, command_func);
int8_t unregisterCommand(const char *);
int8_t registerCommandCR(const char *, command_func);
uint8_t getCurrentCommandCount(void);
uint8_t getCommandIndexFromTable(command_func);

#endif