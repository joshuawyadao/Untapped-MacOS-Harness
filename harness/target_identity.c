/* Report only the current user's stable BSD process identity and executable. */
#include <libproc.h>
#include <sys/proc_info.h>
#include <sys/types.h>

#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int fail(const char *message) {
    fprintf(stderr, "target-identity: %s\n", message);
    return 1;
}

static int parse_pid(const char *text, int *pid) {
    unsigned int value = 0;
    const unsigned char *cursor = (const unsigned char *)text;
    if (*cursor < '1' || *cursor > '9') return 0;
    for (; *cursor != '\0'; ++cursor) {
        if (*cursor < '0' || *cursor > '9') return 0;
        unsigned int digit = (unsigned int)(*cursor - '0');
        if (value > ((unsigned int)INT_MAX - digit) / 10) return 0;
        value = value * 10 + digit;
    }
    *pid = (int)value;
    return 1;
}

int main(int argc, char **argv) {
    if (argc != 2) return fail("expected one canonical positive PID");
    if (getuid() == 0 || getuid() != geteuid())
        return fail("privileged execution refused");

    int pid;
    if (!parse_pid(argv[1], &pid))
        return fail("expected one canonical positive PID");

    struct proc_bsdinfo before = {0};
    struct proc_bsdinfo after = {0};
    if (proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &before, sizeof(before)) != sizeof(before))
        return fail("cannot read target metadata");
    if (before.pbi_pid != (unsigned int)pid || before.pbi_uid != getuid())
        return fail("target PID or user differs");

    char path[PROC_PIDPATHINFO_MAXSIZE] = {0};
    int count = proc_pidpath(pid, path, sizeof(path));
    if (count <= 0 || count >= (int)sizeof(path))
        return fail("cannot read full executable path");
    size_t length = strnlen(path, sizeof(path));
    if (length == 0 || length >= sizeof(path) || path[0] != '/' ||
        strchr(path, '\n') != NULL || strchr(path, '\r') != NULL)
        return fail("invalid executable path");

    if (proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, &after, sizeof(after)) != sizeof(after))
        return fail("cannot recheck target metadata");
    if (after.pbi_pid != before.pbi_pid || after.pbi_uid != before.pbi_uid ||
        after.pbi_start_tvsec != before.pbi_start_tvsec ||
        after.pbi_start_tvusec != before.pbi_start_tvusec)
        return fail("target changed during inspection");

    if (printf("%u %s\n", before.pbi_uid, path) < 0 || fflush(stdout) != 0)
        return fail("cannot write identity");
    return 0;
}
