#include "core_library/io.h"
#include "core_library/utility.h"
#include "core_library/dispatching.h"

SliceU8 readFPGAWrapper(SliceU8 data) {
    ParsedCommand cmd_data;
    uint32_t addr_val;
    cmd_data = ParseCommand(data);
    addr_val = checkAddress(cmd_data.values[1]);
    return readFPGA(addr_val);
}

SliceU8 writeFPGAWrapper(SliceU8 data) {
    ParsedCommand cmd_data;
    uint32_t addr_val;
    cmd_data = ParseCommand(data);
    addr_val = checkAddress(cmd_data.values[1]);
    writeFPGA(addr_val, cmd_data.values[2]);
    return cstr_to_slice(NULL);
}

SliceU8 enterQueueMode(SliceU8 data) {
    (void)data;
    queueMode = 1;
    return cstr_to_slice(NULL);
}

SliceU8 exitQueueMode(SliceU8 data) {
    (void)data;
    queueMode = 0;
    return cstr_to_slice(NULL);
}

SliceU8 runQueueCommands(SliceU8 data) {
    (void)data;
    queueMode = 0;
    executeQueuedCommands();
    return cstr_to_slice(NULL);
}

SliceU8 clearQueue(SliceU8 data) {
    (void)data;
    cmdQueue.head = 0;
    cmdQueue.tail = 0;
    return cstr_to_slice(NULL);
}

SliceU8 printQueueWrapper (SliceU8 data) {
    (void)data;
    printQueuedCommands();
    return cstr_to_slice(NULL);
}

SliceU8 readVersionWrapper (SliceU8 data) {
    (void)data;
    return ReadVersion();
}