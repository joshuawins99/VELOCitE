#ifndef COMMAND_WRAPPERS_H
#define COMMAND_WRAPPERS_H

#include "core_library/slice.h"

SliceU8 readFPGAWrapper(SliceU8);
SliceU8 writeFPGAWrapper(SliceU8);
SliceU8 enterQueueMode(SliceU8);
SliceU8 exitQueueMode(SliceU8);
SliceU8 runQueueCommands(SliceU8);
SliceU8 clearQueue(SliceU8);
SliceU8 printQueueWrapper (SliceU8);
SliceU8 readVersionWrapper (SliceU8);

#endif