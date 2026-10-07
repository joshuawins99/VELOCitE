#include "core_library/fpga_cpu.h"
#include "core_library/dispatching.h"
#include "command_wrappers.h"

#define MAX_COMMANDS 9
static command_entry command_table[MAX_COMMANDS];

void loop() {
    while (1) {
        ReadUART();
    }
}

int main () {
    setCommandsBuffer(command_table, MAX_COMMANDS);

    registerCommand("rFPGA", readFPGAWrapper);
    registerCommand("wFPGA", writeFPGAWrapper);
    registerCommand("readFPGAVersion", readVersionWrapper);
    registerCommand("enterQueue", enterQueueMode);
    registerCommand("exitQueue", exitQueueMode);
    registerCommand("runQueue", runQueueCommands);
    registerCommand("clearQueue", clearQueue);
    registerCommand("printQueue", printQueueWrapper);
    registerCommand("help", commandsList);

    loop();
    return 0;
}
