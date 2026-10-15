/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Verify decoded containment capture pixels. */
#include <png.h>
#include <stdio.h>
#include <stdlib.h>

int
main(int argc, char **argv)
{
	png_image image = { 0 };
	unsigned char *pixels;
	unsigned int low[3] = { 255, 255, 255 }, high[3] = { 0, 0, 0 };
	size_t visible = 0;
	int result = EXIT_FAILURE;

	if (argc != 2) {
		fprintf(stderr, "Usage: %s CAPTURE_PNG\n", argv[0]);
		return EXIT_FAILURE;
	}
	image.version = PNG_IMAGE_VERSION;
	if (!png_image_begin_read_from_file(&image, argv[1])) {
		fprintf(stderr, "PNG header: %s\n", image.message);
		png_image_free(&image);
		return EXIT_FAILURE;
	}
	if (image.width != 320 || image.height != 256) {
		fprintf(stderr, "Expected a 320x256 containment capture\n");
		png_image_free(&image);
		return EXIT_FAILURE;
	}
	image.format = PNG_FORMAT_RGBA;
	pixels = malloc(PNG_IMAGE_SIZE(image));
	if (pixels == NULL) {
		png_image_free(&image);
		return EXIT_FAILURE;
	}
	if (!png_image_finish_read(&image, NULL, pixels, 0, NULL)) {
		fprintf(stderr, "PNG pixels: %s\n", image.message);
		goto out;
	}
	for (size_t i = 0; i < 320U * 256U; i++) {
		const unsigned char *pixel = pixels + i * 4;
		if (pixel[3] < 240)
			continue;
		visible++;
		for (unsigned int c = 0; c < 3; c++) {
			if (pixel[c] < low[c]) low[c] = pixel[c];
			if (pixel[c] > high[c]) high[c] = pixel[c];
		}
	}
	if (visible < 256 ||
	    (high[0] - low[0] < 32 && high[1] - low[1] < 32 && high[2] - low[2] < 32)) {
		fprintf(stderr, "Empty or uniform capture: visible=%zu\n", visible);
		goto out;
	}
	printf("PASS: decoded visible containment content; opaque pixels=%zu\n", visible);
	result = EXIT_SUCCESS;
out:
	free(pixels);
	png_image_free(&image);
	return result;
}
