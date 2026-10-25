/* SPDX-License-Identifier: BSD-2-Clause */
/* Actual core/shim unload regression; no context creation or device scan. */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	unsigned int i;

	if (argc != 2)
		return 2;
	for (i = 0; i < 4; i++) {
		void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);

		if (handle == NULL) {
			fprintf(stderr, "dlopen: %s\n", dlerror());
			return 1;
		}
		/* The two ABIs intentionally have different call signatures. */
		if (dlsym(handle, "iio_has_backend") == NULL) {
			fprintf(stderr, "missing actual IIO backend symbol\n");
			return 1;
		}
		if (dlclose(handle) != 0) {
			fprintf(stderr, "dlclose: %s\n", dlerror());
			return 1;
		}
		printf("unloaded %u\n", i + 1);
		fflush(stdout);
	}
	/* Returning normally must not call code in an already-unloaded DSO. */
	return 0;
}
