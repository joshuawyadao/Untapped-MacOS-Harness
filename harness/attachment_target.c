/* Original inert fixture: announce readiness and exit after 30 seconds. */
#include <stdio.h>
#include <unistd.h>
int main(void) {
    if (getuid() == 0 || getuid() != geteuid()) return 2;
    printf("{\"pid\":%d,\"uid\":%u}\n", getpid(), getuid());
    if (fflush(stdout) != 0) return 3;
    sleep(30);
    return 0;
}
