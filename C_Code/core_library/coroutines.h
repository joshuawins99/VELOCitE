#ifndef COROUTINES_H
#define COROUTINES_H

#include <stdint.h>
#include "slice.h"
#include "dispatching.h"
#include "fpga_cpu.h"
#include "utility.h"

typedef uint32_t pidcr_t;
#define PIDCR_T_MAX UINT32_MAX

#define FUNCTION_SIGNATURE SliceU8 (*func)(SliceU8)
#define RETURN_SIGNATURE cstr_to_slice(NULL)

typedef struct {
    uint16_t pc;
    uint8_t commandIndex;
    void *frame_ptr;
    pidcr_t pid;
} TaskBase;

typedef struct {
    TaskBase base;
    FUNCTION_SIGNATURE;
    SliceU8 initial_data;
    SliceU8 last_return;
    uint8_t finished;
    uint8_t manual_only;
    pidcr_t parent_pid;
    uint8_t is_dead;
} Task;

void frame_free(void *ptr);
void *frame_alloc(void);
TaskBase *get_current_taskbase(void);
pidcr_t scheduler_start(FUNCTION_SIGNATURE, uint32_t cmd_index, SliceU8 data);
void scheduler_tick(void);
void scheduler_kill(pidcr_t pid);
void scheduler_list(void);
pidcr_t scheduler_current_pid(void);
void scheduler_run(void);
void scheduler_resume_pid(pidcr_t pid);
pidcr_t scheduler_start_child(pidcr_t parent_pid, FUNCTION_SIGNATURE, uint32_t cmd_index, SliceU8 data);
pidcr_t scheduler_start_child_manual(pidcr_t parent_pid, FUNCTION_SIGNATURE, uint32_t cmd_index, SliceU8 data);
pidcr_t scheduler_start_root(FUNCTION_SIGNATURE, uint32_t cmd_index, SliceU8 data);
pidcr_t scheduler_pid_is_dead(pidcr_t pid);
void scheduler_init(command_entry *, uint8_t);

#define CR_ASSERT_SPACE_CONCAT(a, b)  a " " b

#define CR_BEGIN() \
    TaskBase *cr_base_begin = get_current_taskbase(); \
    switch (cr_base_begin->pc) { case 0:

#define CR_YIELD() \
    do { \
        TaskBase *cr_base_yield = get_current_taskbase(); \
        cr_base_yield->pc = __LINE__; \
        return RETURN_SIGNATURE; \
        case __LINE__:; \
    } while (0)

#define CR_INIT(f, type) \
    TaskBase *cr_base = get_current_taskbase(); \
    if (cr_base->frame_ptr == NULL) { \
        void *p = frame_alloc(); \
        if (!p) RETURN_SIGNATURE; \
        cr_base->frame_ptr = p; \
        mem_set(p, 0, sizeof(type)); \
        cr_base->pc = 0; \
    } \
    (f) = (type *)cr_base->frame_ptr; \
    _Static_assert(FRAME_SIZE >= sizeof(type), CR_ASSERT_SPACE_CONCAT("FRAME_SIZE is too small for type:", #type)); \
    CR_BEGIN()

#define CR_FINISH(return_val) \
    do { \
        TaskBase *cr_base_finish = get_current_taskbase(); \
        cr_base_finish->pc = 0; \
        return return_val; \
    } while (0); \
}

#define CR_START_CHILD_MANUAL(root_pid, cmd, data) \
    scheduler_start_child_manual(root_pid, &cmd, getCommandIndexFromTable(&cmd), data);

#endif