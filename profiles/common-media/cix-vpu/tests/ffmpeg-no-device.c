/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Real stateful M2M initialization refusal. */
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libavcodec/avcodec.h>
#include <libavutil/error.h>
#include <libavutil/log.h>

static unsigned int missing_device_messages;

static void
observe_log(void *context, int level, const char *format, va_list arguments)
{
	if (strstr(format, "Could not find a valid device") != NULL)
		missing_device_messages++;
	av_log_default_callback(context, level, format, arguments);
}

static int
check_codec(const char *name, int encode)
{
	const AVCodec *codec;
	AVCodecContext *context;
	char message[AV_ERROR_MAX_STRING_SIZE];
	int error;
	unsigned int before;

	codec = encode ? avcodec_find_encoder_by_name(name) :
	    avcodec_find_decoder_by_name(name);
	if (codec == NULL) {
		fprintf(stderr, "Missing required codec: %s\n", name);
		return EXIT_FAILURE;
	}
	context = avcodec_alloc_context3(codec);
	if (context == NULL)
		return EXIT_FAILURE;
	context->width = 64;
	context->height = 64;
	context->pix_fmt = AV_PIX_FMT_NV12;
	context->time_base = (AVRational){ 1, 30 };
	context->framerate = (AVRational){ 30, 1 };
	context->bit_rate = 100000;
	before = missing_device_messages;
	error = avcodec_open2(context, codec, NULL);
	avcodec_free_context(&context);
	if (error != AVERROR(EINVAL) || missing_device_messages != before + 1) {
		fprintf(stderr, "Expected real missing-device refusal from %s (error %d)\n",
		    name, error);
		return EXIT_FAILURE;
	}
	if (av_strerror(error, message, sizeof(message)) != 0)
		return EXIT_FAILURE;
	printf("PASS: %s is registered and refuses absent hardware: %s\n",
	    name, message);
	return EXIT_SUCCESS;
}

int
main(void)
{
	unsigned int cycle;

	/* This focused build must contain no software HEVC fallback. */
	if (avcodec_find_decoder_by_name("hevc") != NULL) {
		fprintf(stderr, "Use the focused M2M-only diagnostic build\n");
		return EXIT_FAILURE;
	}
	av_log_set_callback(observe_log);
	for (cycle = 0; cycle < 4; cycle++) {
		if (check_codec("hevc_v4l2m2m", 0) != EXIT_SUCCESS ||
		    check_codec("hevc_v4l2m2m", 1) != EXIT_SUCCESS)
			return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
