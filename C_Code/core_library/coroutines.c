#include "coroutines.h"
#include "utility.h"
#include "io.h"
#include "dispatching.h"

static Task g_tasks[MAX_TASKS];
static Task *g_current_task = NULL;

static uint8_t frame_pool[MAX_TASKS][FRAME_SIZE];
static uint8_t frame_used[MAX_TASKS];

static pidcr_t next_unique_id = 0;

static command_entry *cmd_table = NULL;
static uint8_t command_count = 0;

void *frame_alloc(void) {
    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        if (!frame_used[i]) {
            frame_used[i] = 1;
            return frame_pool[i];
        }
    }
    return NULL;
}

void frame_free(void *ptr) {
    if (!ptr) return;
    for (int i = 0; i < MAX_TASKS; i++) {
        if ((void *)frame_pool[i] == ptr) {
            frame_used[i] = 0;
            return;
        }
    }
}

int32_t scheduler_pid_to_index(pidcr_t pid) {
    for (int32_t i = 0; i < MAX_TASKS; i++) {
        if (g_tasks[i].func != NULL && g_tasks[i].base.pid == pid) {
            return i;
        }
    }
    return -1;
}

TaskBase *get_current_taskbase(void) {
    return &g_current_task->base;
}

void scheduler_init(command_entry *buffer, uint8_t cmd_count) {
        cmd_table = buffer;
        command_count = cmd_count;
        for(pidcr_t i = 0; i < MAX_TASKS; i++) {
            for (int j = 0; j < FRAME_SIZE; j++) {
                frame_pool[i][j] = 0;
            }
            frame_used[i] = 0;
            g_tasks[i] = (Task){0};

        }
}

pidcr_t scheduler_start(FUNCTION_SIGNATURE, uint32_t cmd_index, SliceU8 data) {
    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        if (g_tasks[i].func == NULL) {
            // zero the task slot
            memset(&g_tasks[i], 0, sizeof(Task));

            // Find PID that is not in use currently
            pidcr_t pid;
            do {
                pid = next_unique_id;

                next_unique_id++;
                if (next_unique_id == PIDCR_T_MAX) {
                    next_unique_id = 0;
                }
            } while (scheduler_pid_to_index(pid) >= 0);

            g_tasks[i].func = func;
            g_tasks[i].initial_data = data;
            g_tasks[i].base.commandIndex = (uint8_t)cmd_index;
            g_tasks[i].base.pc = 0;
            g_tasks[i].base.frame_ptr = NULL;
            g_tasks[i].base.pid = pid;

            return pid;
        }
    }
    return PIDCR_T_MAX; // no free slot
}

void scheduler_tick(void) {
    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        Task *t = &g_tasks[i];

        if (t->func == NULL) continue;
        if (t->manual_only) continue;

        //Print(1, u32_to_ascii(i));
        g_current_task = t;

        SliceU8 result = g_tasks[i].func(t->initial_data);

        TaskBase *tb = &t->base;

        if (tb->pc == 0) {
            t->last_return = result;
            t->finished = 1;
            t->is_dead = 1;
        }
    }
    g_current_task = NULL;
}

void scheduler_kill_pid(pidcr_t pid) {
    int32_t idx = scheduler_pid_to_index(pid);
    if (idx < 0) return; // dead or invalid
    Task *t = &g_tasks[idx];

    if (t->base.frame_ptr) {
        frame_free(t->base.frame_ptr);
    }
    memset(t, 0, sizeof(Task));
    t->is_dead = 1;
}

void scheduler_kill_tree(pidcr_t root_pid) {
    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        Task *t = &g_tasks[i];
        if (t->func != NULL && t->parent_pid == root_pid) {
            scheduler_kill_tree(t->base.pid);
        }
    }

    scheduler_kill_pid(root_pid);
}

uint8_t task_has_children(pidcr_t pid) {
    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        if (g_tasks[i].func != NULL && g_tasks[i].parent_pid == pid) {
            return 1;
        }
    }
    return 0;
}

void scheduler_kill(pidcr_t pid) {
    int32_t idx = scheduler_pid_to_index(pid);
    if (idx < 0) return; // dead or invalid
    Task *t = &g_tasks[idx];

    if (t->func == NULL) return;

    if (task_has_children(pid)) {
        scheduler_kill_tree(pid);
        return;
    }
    scheduler_kill_pid(pid);
}

static void print_tree(pidcr_t parent_pid, int depth) {
    char buf[64];

    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        Task *t = &g_tasks[i];
        if (t->func == NULL) continue;
        if (t->parent_pid != parent_pid) continue;

        const command_entry task_name = cmd_table[t->base.commandIndex];

        // indentation
        for (uint8_t d = 0; d < depth; d++)
            Print(0, "  ");

        // arrow for children
        if (depth > 0)
            Print(0, "-> ");

        // print this node
        str_cpy(buf, "PID: ");
        str_cat(buf, u32_to_ascii(t->base.pid));
        str_cat(buf, " ");
        str_cat(buf, (const char *)task_name.command.ptr);
        Print(1, buf);

        // recursively print this task's children
        print_tree(t->base.pid, depth + 1);
    }
}

void scheduler_list(void) {
    char buf[64];
    uint32_t num_running_processes = 0;
    
    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        if (g_tasks[i].func == NULL) continue;
        num_running_processes++;
    }

    Print(0, "Running Processes (");
    Print(0, u32_to_ascii(num_running_processes));
    Print(1, "):");

    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        Task *t = &g_tasks[i];

        if (t->func == NULL) continue;
        if (t->parent_pid != PIDCR_T_MAX) continue; //Child Process 

        const command_entry task_name = cmd_table[t->base.commandIndex];

        str_cpy(buf, "PID: ");
        str_cat(buf, u32_to_ascii(t->base.pid));
        str_cat(buf, " ");
        str_cat(buf, (const char *)task_name.command.ptr);
        Print(1, buf);

        print_tree(t->base.pid, 1);
    }

    if (num_running_processes == 0) {
        Print(1, "No Running Processes");
    }
}

pidcr_t scheduler_current_pid(void) {
    if (g_current_task) {
        return g_current_task->base.pid;
    }
    return PIDCR_T_MAX;
}

void scheduler_run(void) {
    scheduler_tick();
    for (pidcr_t i = 0; i < MAX_TASKS; i++) {
        if (g_tasks[i].finished) {
            g_tasks[i].finished = 0;
            if (g_tasks[i].last_return.ptr != NULL && g_tasks[i].last_return.len > 0) {
                PrintSlice(1, g_tasks[i].last_return);
            }
            Task *t = &g_tasks[i];
            TaskBase *tb = &t->base;
            frame_free(tb->frame_ptr);
            tb->frame_ptr = NULL;
            t->func = NULL;
        }
    }
}

void scheduler_resume_pid(pidcr_t pid) {
    int32_t idx = scheduler_pid_to_index(pid);
    if (idx < 0) return; // dead or invalid
    Task *t = &g_tasks[idx];

    if (t->func == NULL) return;

    Task *prev = g_current_task;
    g_current_task = t;

    SliceU8 result = t->func(t->initial_data);

    TaskBase *tb = &t->base;

    if (tb->pc == 0 && tb->frame_ptr != NULL) {
        t->last_return = result;
        t->finished = 1;
        t->is_dead = 1;
    }
    g_current_task = prev;
}

pidcr_t scheduler_start_child(pidcr_t parent_pid, FUNCTION_SIGNATURE, uint32_t cmd_index, SliceU8 data) {
    pidcr_t pid = scheduler_start(func, cmd_index, data);
    int32_t idx = scheduler_pid_to_index(pid);
    if (idx < 0) return PIDCR_T_MAX;
    g_tasks[idx].parent_pid = parent_pid;
    return pid;
}

pidcr_t scheduler_start_child_manual(pidcr_t parent_pid, FUNCTION_SIGNATURE, uint32_t cmd_index, SliceU8 data) {
    pidcr_t pid = scheduler_start(func, cmd_index, data);
    int32_t idx = scheduler_pid_to_index(pid);
    if (idx < 0) return PIDCR_T_MAX;
    g_tasks[idx].parent_pid = parent_pid;
    g_tasks[idx].manual_only = 1;
    return pid;
}

pidcr_t scheduler_start_root(FUNCTION_SIGNATURE, uint32_t cmd_index, SliceU8 data) {
    pidcr_t pid = scheduler_start(func, cmd_index, data);
    int32_t idx = scheduler_pid_to_index(pid);
    if (idx < 0) return PIDCR_T_MAX;
    g_tasks[idx].parent_pid = PIDCR_T_MAX; // no parent
    return pid;
}

pidcr_t scheduler_pid_is_dead(pidcr_t pid) {
    int32_t idx = scheduler_pid_to_index(pid);
    if (idx < 0) return 1; // dead or invalid
    Task *t = &g_tasks[idx];
    return t->is_dead;
}
