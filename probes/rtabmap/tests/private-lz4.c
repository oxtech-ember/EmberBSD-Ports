/* SPDX-License-Identifier: MIT
 * AI-assisted implementation for the EmberBSD RTAB-Map port.
 * Load RTAB-Map before the common codec to expose private symbol collisions.
 */
#include <dlfcn.h>
#include <lz4.h>
#include <stdio.h>
#include <string.h>

#if LZ4_VERSION_NUMBER != 11000
#error This contract requires the shared LZ4 1.10.0 headers.
#endif

int main(int argc, char **argv)
{
    void *handles[3] = {NULL, NULL, NULL};
    int (*version_number)(void) = NULL;
    int result = 1;
    if (argc != 4) {
        fprintf(stderr, "usage: %s RTABMAP_CORE FLANN_CPP COMMON_LZ4\n", argv[0]);
        return 64;
    }
    for (int i = 0; i < 3; ++i) {
        handles[i] = dlopen(argv[i + 1], RTLD_NOW | RTLD_GLOBAL);
        if (handles[i] == NULL) {
            fprintf(stderr, "dlopen %s: %s\n", argv[i + 1], dlerror());
            goto done;
        }
    }
    dlerror();
    void *symbol = dlsym(RTLD_DEFAULT, "LZ4_versionNumber");
    const char *error = dlerror();
    if (error != NULL || symbol == NULL) {
        fprintf(stderr, "dlsym LZ4_versionNumber: %s\n", error ? error : "missing symbol");
        goto done;
    }
    /* POSIX dlsym permits a function address. Avoid a non-ISO pointer cast. */
    _Static_assert(sizeof(version_number) == sizeof(symbol), "POSIX function address size");
    memcpy(&version_number, &symbol, sizeof(version_number));
    const int version = version_number();
    if (version != LZ4_VERSION_NUMBER) {
        fprintf(stderr, "common LZ4 version mismatch: got %d, expected %d\n",
                version, LZ4_VERSION_NUMBER);
        goto done;
    }
    printf("common LZ4 version: %d\n", version);
    result = 0;
done:
    for (int i = 2; i >= 0; --i) {
        if (handles[i] != NULL && dlclose(handles[i]) != 0) {
            fprintf(stderr, "dlclose: %s\n", dlerror());
            result = 1;
        }
    }
    return result;
}
