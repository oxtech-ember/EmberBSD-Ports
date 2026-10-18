/* Origin: MIT Kerberos 1.22.2 configure probe, MIT license. */
#include <stdio.h>
#include <string.h>
const char expected[] = "200 100";
int main() {
    char buf[30];
    sprintf(buf, "%2$x %1$d", 100, 512);
    if (strcmp(expected, buf)) {
        fprintf(stderr, "bad result: <%s> wanted: <%s>\n", buf, expected);
        return 1;
    }
    return 0;
}
