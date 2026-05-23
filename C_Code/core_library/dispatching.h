#ifndef DISPATCHING_H
#define DISPATCHING_H

#include "slice.h"

#define MAX_CMD_QUEUE 32
#define MAX_LINE_LENGTH 40

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
} command_entry;

extern CommandQueue cmdQueue;
extern uint8_t queueMode;

uint8_t isQueueFull();
uint8_t isQueueEmpty();
void enqueueCommand(const SliceU8);
SliceU8 dequeueCommand();
void executeQueuedCommands();
void printQueuedCommands();
SliceU8 commandsList(SliceU8);
SliceU8 executeCommands(SliceU8);
void UARTCommand(SliceU8);
void ReadUART();
void setCommandsBuffer(command_entry *, uint8_t);
int8_t registerCommand(const char *, command_func);

#endif