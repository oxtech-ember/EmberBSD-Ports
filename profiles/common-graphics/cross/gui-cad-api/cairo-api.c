/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD; AI-assisted Cairo image and document API checks.
 */
#include "loaded.h"
#include <cairo.h>
#include <cairo-pdf.h>
#include <cairo-svg.h>
#include <stdint.h>

struct stream {
	unsigned char bytes[16384];
	size_t length;
	size_t offset;
};

static cairo_status_t
write_bytes(void *data, const unsigned char *bytes, unsigned int length)
{
	struct stream *stream = data;

	if (length > sizeof(stream->bytes) - stream->length)
		return CAIRO_STATUS_WRITE_ERROR;
	memcpy(stream->bytes + stream->length, bytes, length);
	stream->length += length;
	return CAIRO_STATUS_SUCCESS;
}

static cairo_status_t
read_bytes(void *data, unsigned char *bytes, unsigned int length)
{
	struct stream *stream = data;

	if (length > stream->length - stream->offset)
		return CAIRO_STATUS_READ_ERROR;
	memcpy(bytes, stream->bytes + stream->offset, length);
	stream->offset += length;
	return CAIRO_STATUS_SUCCESS;
}

static cairo_status_t
reject_write(void *data, const unsigned char *bytes, unsigned int length)
{

	(void)data;
	(void)bytes;
	(void)length;
	return CAIRO_STATUS_WRITE_ERROR;
}

static void
require(int condition, const char *message)
{

	if (!condition) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(1);
	}
}

static void
paint(cairo_surface_t *surface)
{
	cairo_t *context = cairo_create(surface);

	cairo_set_operator(context, CAIRO_OPERATOR_SOURCE);
	cairo_set_source_rgb(context, 0, 0, 1);
	cairo_paint(context);
	cairo_set_source_rgb(context, 1, 0, 0);
	cairo_rectangle(context, 0, 0, 4, 4);
	cairo_fill(context);
	require(cairo_status(context) == CAIRO_STATUS_SUCCESS, "Cairo draw");
	cairo_destroy(context);
}

static void
pixels(cairo_surface_t *surface)
{
	unsigned char *bytes;
	int x, y, stride;
	uint32_t actual, expected;

	require(cairo_surface_status(surface) == CAIRO_STATUS_SUCCESS,
	    "Cairo surface status");
	require(cairo_image_surface_get_width(surface) == 8 &&
	    cairo_image_surface_get_height(surface) == 8, "image dimensions");
	cairo_surface_flush(surface);
	bytes = cairo_image_surface_get_data(surface);
	stride = cairo_image_surface_get_stride(surface);
	for (y = 0; y < 8; y++) {
		for (x = 0; x < 8; x++) {
			memcpy(&actual, bytes + y * stride + x * 4, sizeof(actual));
			expected = x < 4 && y < 4 ? 0xffff0000U : 0xff0000ffU;
			require(actual == expected, "exact premultiplied ARGB pixel");
		}
	}
}

int
main(int argc, char **argv)
{
	struct stream stream;
	cairo_surface_t *image, *decoded, *document;
	unsigned int iteration;

	(void)argc;
	for (iteration = 0; iteration < 4; iteration++) {
		memset(&stream, 0, sizeof(stream));
		image = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, 8, 8);
		paint(image);
		pixels(image);
		require(cairo_surface_write_to_png_stream(image, write_bytes,
		    &stream) == CAIRO_STATUS_SUCCESS, "PNG encoding");
		decoded = cairo_image_surface_create_from_png_stream(read_bytes,
		    &stream);
		pixels(decoded);
		cairo_surface_destroy(decoded);
		require(cairo_surface_write_to_png_stream(image, reject_write,
		    NULL) == CAIRO_STATUS_WRITE_ERROR, "PNG writer failure");
		cairo_surface_destroy(image);

		memset(&stream, 0, sizeof(stream));
		decoded = cairo_image_surface_create_from_png_stream(read_bytes,
		    &stream);
		require(cairo_surface_status(decoded) == CAIRO_STATUS_READ_ERROR,
		    "truncated PNG reader failure");
		cairo_surface_destroy(decoded);

		memset(&stream, 0, sizeof(stream));
		document = cairo_pdf_surface_create_for_stream(write_bytes,
		    &stream, 8, 8);
		paint(document);
		cairo_surface_finish(document);
		require(cairo_surface_status(document) == CAIRO_STATUS_SUCCESS &&
		    stream.length > 8 && memcmp(stream.bytes, "%PDF-1.", 7) == 0,
		    "PDF document output");
		cairo_surface_destroy(document);

		memset(&stream, 0, sizeof(stream));
		document = cairo_svg_surface_create_for_stream(write_bytes,
		    &stream, 8, 8);
		paint(document);
		cairo_surface_finish(document);
		require(cairo_surface_status(document) == CAIRO_STATUS_SUCCESS &&
		    stream.length < sizeof(stream.bytes), "SVG document output");
		stream.bytes[stream.length] = '\0';
		require(strstr((char *)stream.bytes, "<svg") != NULL,
		    "SVG element");
		cairo_surface_destroy(document);

		document = cairo_pdf_surface_create_for_stream(reject_write,
		    NULL, 8, 8);
		paint(document);
		cairo_surface_finish(document);
		require(cairo_surface_status(document) == CAIRO_STATUS_WRITE_ERROR,
		    "PDF writer failure");
		cairo_surface_destroy(document);
	}
	cairo_debug_reset_static_data();
	check_loaded(argv[0]);
	puts("PASS: Cairo exact pixels, PNG round trip, PDF/SVG and I/O failures, four lifecycles");
	return 0;
}
