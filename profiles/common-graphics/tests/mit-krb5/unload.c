/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    void *handles[4], *library, *loaded;
    char path[4096];
    const char *dependencies[] = {"libkrb5support.so.0", "libcom_err.so.3", "libk5crypto.so.3", "libkrb5.so.3"};
    size_t i;
    if (argc != 2) return 2;
    for (i = 0; i < 4; i++) {
        int n = snprintf(path, sizeof(path), "%s/%s", argv[1], dependencies[i]);
        if (n < 0 || (size_t)n >= sizeof(path)) return 2;
        handles[i] = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
        if (handles[i] == NULL) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    }
    if (snprintf(path, sizeof(path), "%s/libgssapi_krb5.so.2", argv[1]) >= (int)sizeof(path)) return 2;
    library = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (library == NULL) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    if (dlclose(library) != 0) return 2;
    loaded = dlopen(path, RTLD_NOW | RTLD_NOLOAD);
    if (loaded == NULL) {
        puts("FAIL: configured unload prevention was lost by libtool");
        return 1;
    }
    if (dlclose(loaded) != 0) return 2;
    for (i = 4; i > 0; i--) if (dlclose(handles[i - 1]) != 0) return 2;
    puts("PASS: installed MIT GSS library remains mapped after dlclose");
    return 0;
}
