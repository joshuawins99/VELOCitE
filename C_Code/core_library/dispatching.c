#include "io.h"
#include "utility.h"
#include "dispatching.h"
#include "coroutines.h"

static command_entry *cmd_table = NULL;
static uint8_t cmd_capacity = 0;
static uint8_t command_count = 0;

CommandQueue cmdQueue = { .head = 0, .tail = 0 };
uint8_t queueMode = 0; // 0 = immediate, 1 = queue mode

uint8_t isQueueFull() {
    return cmdQueue.tail >= MAX_CMD_QUEUE;
}

uint8_t isQueueEmpty() {
    return cmdQueue.head == cmdQueue.tail;
}

void enqueueCommand(SliceU8 data) {
    uint8_t i = 0;

    if (!isQueueFull()) {
        while (i < data.len) {
            cmdQueue.commands[cmdQueue.tail][i] = data.ptr[i];
            ++i;
        }
        cmdQueue.slice_lengths[cmdQueue.tail] = data.len;
        cmdQueue.commands[cmdQueue.tail][i] = '\0';

        ++cmdQueue.tail;
    }
}

SliceU8 dequeueCommand() {
    uint8_t idx = cmdQueue.head;
    
    if (!isQueueEmpty()) {
        ++cmdQueue.head;
        return slice_range((unsigned char *)cmdQueue.commands[idx], 0, cmdQueue.slice_lengths[idx]);
    }
    return cstr_to_slice(NULL);
}

void executeQueuedCommands() {
    SliceU8 cmd;
    SliceU8 result;

    while (!isQueueEmpty()) {
        cmd = dequeueCommand();
        result = executeCommands(cmd);
        if (result.ptr != NULL && result.len > 0) {
            PrintSlice(1, result);
        }
    }
}

void printQueuedCommands() {
    uint8_t i;
    char label[8];
    char *index_str;

    if (isQueueEmpty()) {
        Print(1, "Command queue empty");
        return;
    }

    for (i = cmdQueue.head; i < cmdQueue.tail; ++i) {
        index_str = u32_to_ascii(i - cmdQueue.head);

        str_cpy(label, index_str); // copy index into label
        str_cat(label, ": "); // append ": " to the end

        Print(0, label);
        PrintSlice(1, slice_range((unsigned char *)cmdQueue.commands[i], 0, cmdQueue.slice_lengths[i]));
    }
}

SliceU8 commandsList (SliceU8 data) {
    (void)data;
    uint8_t i;

    Print(1, "Available Commands:");
    for (i = 0; i < command_count; ++i) {
        Print(1,(char *)cmd_table[i].command.ptr);
    }
    return cstr_to_slice(NULL);
}

SliceU8 executeCommands(SliceU8 data) {
    uint8_t i;
    
    for (i = 0; i < command_count; ++i) {
        if (stringMatchSlicePrefix(data, cmd_table[i].command) == 1) {
            if (queueMode == 1 && stringMatchSlicePrefix(cstr_to_slice("exitQueue"), cmd_table[i].command) != 1) {
                enqueueCommand(data);
                return cstr_to_slice(NULL);
            }
            if (cmd_table[i].is_coroutine == 1) { 
                scheduler_start_root(cmd_table[i].func, cmd_table[i].index, data);
                return cstr_to_slice(NULL);
            }
            return cmd_table[i].func(data);
        }
    }
    return cstr_to_slice(NULL);
}

void UARTCommand (SliceU8 data) {
    SliceU8 commandOutput;

    commandOutput = executeCommands(data);
    if (commandOutput.ptr != NULL && commandOutput.len > 0) {
        PrintSlice(1, commandOutput);
    }
}

//Incoming UART Line Buffer and Index
static uint8_t char_iter;
static char readuart[MAX_LINE_LENGTH];

#ifdef REPL_UART
static uint8_t cursor_placed = 0;
#endif

#ifdef REPL_UART
void read_line() {
    char c;
    
    char_iter = 0;
    while ((c = get_char()) != '\n' && c != '\r' && char_iter < MAX_LINE_LENGTH - 1) {
        if (c == 8 || c == 127) { //Backspace or DEL
            if (char_iter > 0) {
                char_iter--;
                Print(0, "\b \b");
            }
        } else {
            readuart[char_iter++] = c;
            put_char(c);
        }
    }
#ifndef CARRIAGE_RETURN
    put_char('\n');
#else
    Print(0, "\r\n");
#endif
}
#endif

void ReadUART() {
#ifndef REPL_UART
    if (ReadIO(UART_CPU_BaseAddress+(4*ADDR_WORD)) == 1) return;
    char c;

    c = get_char();
    if (c != '\n') {
        readuart[char_iter] = c;
        ++char_iter;
    } else {
        UARTCommand(slice_range((uint8_t *)readuart, 0, char_iter));
        char_iter = 0;
    }
#else
    if (cursor_placed == 0) {
        if (queueMode == 1) {
            Print(0, "[Queue] > ");
        } else {
            Print(0, "> ");
        }
        cursor_placed = 1;
    }
    if (ReadIO(UART_CPU_BaseAddress+(4*ADDR_WORD)) == 1) return;
    read_line();
    cursor_placed = 0;
    UARTCommand(slice_range((uint8_t *)readuart, 0, char_iter));
#endif
}

void setCommandsBuffer(command_entry *buffer, uint8_t capacity) {
    cmd_table = buffer;
    cmd_capacity = capacity;
    command_count = 0;
}

int8_t registerCommand(const char *name, command_func func) {
    if (command_count >= cmd_capacity) {
        return -1;
    }

    command_entry *c = &cmd_table[command_count++];
    c->command = cstr_to_slice((char *)name);
    c->func = func;
    c->index = command_count - 1;
    c->is_coroutine = 0;

    return 0;
}

int8_t registerCommandCR(const char *name, command_func func) {
    if (command_count >= cmd_capacity) {
        return -1;
    }

    command_entry *c = &cmd_table[command_count++];
    c->command = cstr_to_slice((char *)name);
    c->func = func;
    c->index = command_count - 1;
    c->is_coroutine = 1;

    return 0;
}

uint8_t getCurrentCommandCount() {
    return command_count;
}

uint8_t getCommandIndexFromTable(command_func func) {
    for (uint8_t i = 0; i < command_count; i++) {
        if (func == cmd_table[i].func) {
            return i;
        }
    }
    return 0;
}