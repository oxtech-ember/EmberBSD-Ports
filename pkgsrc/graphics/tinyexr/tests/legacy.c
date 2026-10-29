/* SPDX-License-Identifier: BSD-2-Clause */
#include <tinyexr.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

int
main(void)
{
	float pixels[64 * 64 * 4], *out = NULL;
	const char *err = NULL;
	int h = 0, i, w = 0;

	for (i = 0; i < 64 * 64 * 4; i++)
		pixels[i] = (float)(i % 16) / 16.0f;
	if (SaveEXR(pixels, 64, 64, 4, 0, "image.exr", &err) != 0) {
		fprintf(stderr, "save: %s\n", err);
		return 1;
	}
	if (LoadEXR(&out, &w, &h, "image.exr", &err) != 0) {
		fprintf(stderr, "load: %s\n", err);
		return 2;
	}
	if (w != 64 || h != 64)
		return 3;
	for (i = 0; i < 64 * 64 * 4; i++) {
		if (fabsf(out[i] - pixels[i]) > 0.0001f)
			return 4;
	}
	free(out);
	puts("legacy EXR roundtrip PASS");
	return 0;
}
