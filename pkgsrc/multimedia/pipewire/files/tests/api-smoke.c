#include <pipewire/pipewire.h>
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv)
{
    const char *runtime;
    pw_init(&argc, &argv);
    runtime = pw_get_library_version();
    if (!runtime || strcmp(runtime, pw_get_headers_version()) != 0) {
        fputs("PipeWire header/library version mismatch\n", stderr);
        pw_deinit();
        return 1;
    }
    printf("PipeWire %s\n", runtime);
    pw_deinit();
    return 0;
}
