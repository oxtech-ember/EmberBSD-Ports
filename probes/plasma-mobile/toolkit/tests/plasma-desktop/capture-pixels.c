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
	unsigned int low[6] = { 255, 255, 255, 255, 255, 255 };
	unsigned int high[6] = { 0 };
	unsigned long visible = 0;
	int contrast = 0;
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
	pixels = malloc(320U * 256U * 4U);
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
		if (pixel[3] >= 240)
			visible++;
		/* Composite on both backgrounds to include monochrome alpha content. */
		for (unsigned int c = 0; c < 6; c++) {
			unsigned int value = pixel[c % 3] * pixel[3] / 255U;
			if (c >= 3)
				value += 255U - pixel[3];
			if (value < low[c])
				low[c] = value;
			if (value > high[c])
				high[c] = value;
		}
	}
	for (unsigned int c = 0; c < 6; c++)
		if (high[c] - low[c] >= 32)
			contrast = 1;
	if (visible < 256 || !contrast) {
		fprintf(stderr, "Empty or uniform capture: visible=%lu\n", visible);
		goto out;
	}
	printf("PASS: decoded visible containment content; opaque pixels=%lu\n", visible);
	result = EXIT_SUCCESS;
out:
	free(pixels);
	png_image_free(&image);
	return result;
}
