/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Installed TIFF/JBIG consumer regression. */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <tiffio.h>

int
main(int argc, char **argv)
{
	unsigned char input[8] = { 0x81, 0x42, 0x24, 0x18, 0x18, 0x24, 0x42, 0x81 };
	unsigned char output[8];
	TIFF *image = NULL;
	uint16_t compression = 0;
	int fd = -1, status = 1;

	if (argc != 2)
		return 2;
	fd = open(argv[1], O_RDWR | O_CREAT | O_EXCL, 0600);
	if (fd == -1)
		return 2;
	image = TIFFFdOpen(fd, argv[1], "w");
	if (image == NULL)
		goto out;
	fd = -1;
	if (!TIFFSetField(image, TIFFTAG_IMAGEWIDTH, 8) ||
	    !TIFFSetField(image, TIFFTAG_IMAGELENGTH, 8) ||
	    !TIFFSetField(image, TIFFTAG_BITSPERSAMPLE, 1) ||
	    !TIFFSetField(image, TIFFTAG_SAMPLESPERPIXEL, 1) ||
	    !TIFFSetField(image, TIFFTAG_ROWSPERSTRIP, 8) ||
	    !TIFFSetField(image, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG) ||
	    !TIFFSetField(image, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISWHITE) ||
	    !TIFFSetField(image, TIFFTAG_COMPRESSION, COMPRESSION_JBIG))
		goto out;
	if (TIFFWriteEncodedStrip(image, 0, input, sizeof(input)) != (tmsize_t)sizeof(input))
		goto out;
	TIFFClose(image);
	image = TIFFOpen(argv[1], "r");
	if (image == NULL)
		goto out;
	if (!TIFFGetField(image, TIFFTAG_COMPRESSION, &compression) ||
	    compression != COMPRESSION_JBIG ||
	    TIFFReadEncodedStrip(image, 0, output, sizeof(output)) != (tmsize_t)sizeof(output) ||
	    memcmp(input, output, sizeof(input)) != 0)
		goto out;
	puts("PASS: installed TIFF encodes and decodes exact pixels through current JBIG");
	status = 0;
out:
	if (image != NULL)
		TIFFClose(image);
	if (fd != -1)
		close(fd);
	return status;
}
