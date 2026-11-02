/* Original fixture-only task-port probe. Never reads or writes target memory. */
#include <libproc.h>
#include <mach/mach.h>
#include <sys/proc_info.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int main(int argc, char **argv) {
    if (argc != 3 || getuid() == 0 || getuid() != geteuid()) return 2;
    unsigned long number = 0;
    if (argv[1][0] < '1' || argv[1][0] > '9') return 2;
    for (const char *p = argv[1]; *p; ++p) {
        if (*p < '0' || *p > '9' || number > (INT_MAX - (*p - '0')) / 10UL) return 2;
        number = number * 10 + (*p - '0');
    }
    pid_t pid = (pid_t)number;
    struct proc_bsdinfo info = {0};
    char path[PROC_PIDPATHINFO_MAXSIZE] = {0};
    if (argv[2][0] != '/' ||
        proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &info, sizeof(info)) != sizeof(info) ||
        info.pbi_uid != getuid() || info.pbi_pid != (unsigned int)pid ||
        proc_pidpath(pid, path, sizeof(path)) <= 0 || strcmp(path, argv[2]) != 0) return 3;
    mach_port_t port = MACH_PORT_NULL;
    kern_return_t code = task_for_pid(mach_task_self(), pid, &port);
    int acquired = code == KERN_SUCCESS && MACH_PORT_VALID(port);
    pid_t port_pid = 0;
    int port_matches = !acquired ||
        (pid_for_task(port, &port_pid) == KERN_SUCCESS && port_pid == pid);
    if (MACH_PORT_VALID(port)) mach_port_deallocate(mach_task_self(), port);
    struct proc_bsdinfo after = {0};
    char after_path[PROC_PIDPATHINFO_MAXSIZE] = {0};
    if (!port_matches ||
        proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &after, sizeof(after)) != sizeof(after) ||
        after.pbi_uid != info.pbi_uid || after.pbi_pid != info.pbi_pid ||
        after.pbi_start_tvsec != info.pbi_start_tvsec ||
        after.pbi_start_tvusec != info.pbi_start_tvusec ||
        proc_pidpath(pid, after_path, sizeof(after_path)) <= 0 ||
        strcmp(after_path, path) != 0) return 3;
    printf("{\"pid\":%d,\"uid\":%u,\"kern_return\":%d,\"acquired\":%s}\n",
           pid, getuid(), code, acquired ? "true" : "false");
    return fflush(stdout) == 0 ? 0 : 4;
}
