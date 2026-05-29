#include "io.h"
#include "utility.h"

char get_char(void) {
    while (ReadIO(UART_CPU_BaseAddress+(4*ADDR_WORD)) != 0);
    return ReadIO(UART_CPU_BaseAddress+(3*ADDR_WORD));
}

void put_char(uint8_t c) {
    while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0);
    WriteIO(UART_CPU_BaseAddress, (uint8_t)c);
    WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
}

void Print(uint8_t line, const char *data) {
    while (*data) {
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0); // wait until UART not busy
        WriteIO(UART_CPU_BaseAddress, *data++);
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
    }
    if (line) {
#ifdef CARRIAGE_RETURN
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0);
        WriteIO(UART_CPU_BaseAddress, '\r');
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
#endif
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0);
        WriteIO(UART_CPU_BaseAddress, '\n');
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
    }
}

void PrintSlice(uint8_t line, const SliceU8 data) {
    char *ptr = (char *)data.ptr; // Printing ascii so use char
    slen_t length = data.len;

    while (length--) {
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0); // wait until UART not busy
        WriteIO(UART_CPU_BaseAddress, *ptr++);
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
    }
    if (line) {
#ifdef CARRIAGE_RETURN
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0);
        WriteIO(UART_CPU_BaseAddress, '\r');
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
#endif
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0);
        WriteIO(UART_CPU_BaseAddress, '\n');
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
    }
}

SliceU8 ReadVersion(void) {
    static char readversion[VersionStringSize];
    char current_char;
    uint8_t count = 0;
    uint8_t i;

    for (i = 0; i < VersionStringSize; ++i) {
        current_char = (char) ReadIO(Version_String_BaseAddress+(i*ADDR_WORD));
        if (current_char == '\0') {
            ++count;
        } else {
            readversion[i-count] = current_char;
        }
    }
    
    return slice_range((uint8_t *)readversion, 0, (i-count));
}

SliceU8 readFPGA(uint32_t addr) {
    char *rd_data;
    
    rd_data = u32_to_ascii(ReadIO32(addr));
    return cstr_to_slice(rd_data);
}

void writeFPGA(uint32_t addr, uint32_t data) {
    WriteIO32(addr, data);
}
