/* Emit potential game/Steam rows and unresolved PIDs from a fresh macOS process snapshot. */
#include <errno.h>
#include <libproc.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/proc.h>
#include <sys/sysctl.h>
#include <unistd.h>
#include <vis.h>

static int snapshot(struct kinfo_proc **rows, size_t *capacity, size_t *count) {
    int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_ALL, 0};
    for (int attempt = 0; attempt < 3; ++attempt) {
        size_t size = *capacity;
        if (*rows != NULL) {
            if (sysctl(mib, 4, *rows, &size, NULL, 0) == 0) {
                if (size == 0 || size % sizeof(**rows) != 0) return -1;
                *count = size / sizeof(**rows);
                return 0;
            }
            if (errno != ENOMEM) return -1;
        }
        if (sysctl(mib, 4, NULL, &size, NULL, 0) != 0 || size > 32 * 1024 * 1024)
            return -1;
        size += 64 * sizeof(**rows);
        struct kinfo_proc *grown = realloc(*rows, size);
        if (grown == NULL) return -1;
        *rows = grown;
        *capacity = size;
    }
    return -1;
}

static const char *command_line_name(pid_t pid, char *buffer, size_t size) {
    int mib[] = {CTL_KERN, KERN_PROCARGS2, pid};
    if (sysctl(mib, 3, buffer, &size, NULL, 0) != 0 || size <= sizeof(int)) return NULL;

    int argc;
    memcpy(&argc, buffer, sizeof(argc));
    if (argc <= 0) return NULL;
    char *end = buffer + size;
    /* The initial int is followed by the saved executable path, then argv. */
    char *cursor = memchr(buffer + sizeof(argc), '\0', size - sizeof(argc));
    if (cursor == NULL) return NULL;
    while (cursor < end && *cursor == '\0') ++cursor;
    if (cursor == end || memchr(cursor, '\0', (size_t)(end - cursor)) == NULL) return NULL;
    return cursor;
}

static int might_match(const char *command) {
    /* A broad filter only. The launcher still applies its exact candidate rules. */
    return strstr(command, "Slay the Spire 2") != NULL || strcasestr(command, "steam") != NULL;
}

static int process_gone(const struct kinfo_proc *original) {
    int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_PID, original->kp_proc.p_pid};
    struct kinfo_proc current;
    size_t size = sizeof(current);
    if (sysctl(mib, 4, &current, &size, NULL, 0) != 0) return 0;
    return size == 0 || (size == sizeof(current) && current.kp_proc.p_stat == SZOMB);
}

static int scan(const struct kinfo_proc *rows, size_t count, char *args, size_t argmax,
                char *escaped, size_t escaped_size, uid_t own_uid) {
    int incomplete = 0;
    for (size_t i = 0; i < count; ++i) {
        const struct kinfo_proc *row = &rows[i];
        pid_t pid = row->kp_proc.p_pid;
        if (pid <= 0 || row->kp_proc.p_stat == SZOMB) continue;
        uid_t uid = row->kp_eproc.e_ucred.cr_uid;
        const char *command = uid == own_uid ? command_line_name(pid, args, argmax) : NULL;
        char path[PROC_PIDPATHINFO_MAXSIZE];
        if (command == NULL) {
            int length = proc_pidpath(pid, path, sizeof(path));
            if (length <= 0 || (size_t)length >= sizeof(path)) {
                if ((uid != own_uid || might_match(row->kp_proc.p_comm)) && !process_gone(row)) {
                    if (printf("? %d %u\n", pid, uid) < 0) return -1;
                    incomplete = 1;
                }
                continue;
            }
            command = path;
        }
        if (!might_match(command)) continue;
        if (strnvis(escaped, escaped_size, command, VIS_TAB | VIS_NL | VIS_NOSLASH) < 0 ||
            printf("%d %u %s\n", pid, uid, escaped) < 0) return -1;
    }
    return incomplete;
}

int main(void) {
    uid_t uid = getuid();
    if (uid == 0 || uid != geteuid()) return 1;
    setlocale(LC_ALL, "");

    int mib[] = {CTL_KERN, KERN_ARGMAX};
    int argmax;
    size_t size = sizeof(argmax);
    if (sysctl(mib, 2, &argmax, &size, NULL, 0) != 0 || size != sizeof(argmax) ||
        argmax < PROC_PIDPATHINFO_MAXSIZE || argmax > 4 * 1024 * 1024) return 1;
    size_t escaped_size = (size_t)argmax * 4 + 1;
    char *args = malloc((size_t)argmax);
    char *escaped = malloc(escaped_size);
    struct kinfo_proc *rows = NULL;
    size_t capacity = 0, count = 0;
    int request, status = 0;
    if (args == NULL || escaped == NULL) status = 1;
    while (status == 0 && (request = getchar()) != EOF) {
        if (request != '\n' || snapshot(&rows, &capacity, &count) != 0) {
            status = 1;
            break;
        }
        int result = scan(rows, count, args, (size_t)argmax, escaped, escaped_size, uid);
        /* One terminal byte per request. Status 1 requires the caller to resolve all marked rows. */
        if (result < 0 || fputc(result, stdout) == EOF || fflush(stdout) == EOF) status = 1;
    }
    free(rows);
    free(escaped);
    free(args);
    return status;
}
