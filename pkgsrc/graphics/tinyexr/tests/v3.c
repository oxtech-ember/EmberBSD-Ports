/* SPDX-License-Identifier: BSD-2-Clause */
#include <exr.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int
main(void)
{
	exr_image in = {0}, out = {0};
	exr_compression modes[] = {
		EXR_COMPRESSION_NONE, EXR_COMPRESSION_RLE,
		EXR_COMPRESSION_ZIPS, EXR_COMPRESSION_ZIP,
		EXR_COMPRESSION_PIZ, EXR_COMPRESSION_PXR24,
		EXR_COMPRESSION_B44, EXR_COMPRESSION_B44A,
		EXR_COMPRESSION_ZSTD
	};
	size_t i, len;
	void *buf;
	int c;

	if (exr_load_from_file("image.exr", NULL, &in) != EXR_SUCCESS)
		return 1;
	for (i = 0; i < sizeof(modes) / sizeof(modes[0]); i++) {
		buf = NULL;
		len = 0;
		if (exr_save_to_memory(&buf, &len, NULL, &in, modes[i]) != EXR_SUCCESS)
			return 2;
		if ((modes[i] == EXR_COMPRESSION_ZSTD ||
		    modes[i] == EXR_COMPRESSION_ZIP) && len >= 64 * 64 * 16)
			return 5;
		if (exr_load_from_memory(buf, len, NULL, &out) != EXR_SUCCESS ||
		    out.num_parts != 1 || out.parts[0].width != 64 ||
		    out.parts[0].height != 64)
			return 3;
		if (modes[i] != EXR_COMPRESSION_PXR24 &&
		    modes[i] != EXR_COMPRESSION_B44 &&
		    modes[i] != EXR_COMPRESSION_B44A) {
			for (c = 0; c < in.parts[0].header.num_channels; c++) {
				if (memcmp(in.parts[0].images[c], out.parts[0].images[c],
				    64 * 64 * 4) != 0)
					return 4;
			}
		}
		exr_image_free(&out);
		free(buf);
	}
	exr_image_free(&in);
	puts("v3 EXR nine compression roundtrips PASS");
	return 0;
}
