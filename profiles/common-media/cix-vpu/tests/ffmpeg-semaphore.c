/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). POSIX lifecycle regression; no device mock. */
#include <errno.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>

#include <libavcodec/avcodec.h>
#include <libavutil/error.h>

int __real_sem_init(sem_t *, int, unsigned int);
int __real_sem_destroy(sem_t *);
int __wrap_sem_init(sem_t *, int, unsigned int);
int __wrap_sem_destroy(sem_t *);

static unsigned int init_calls, destroy_calls, live_semaphores, violations;
static sem_t *live_semaphore;
static int fail_init;

int
__wrap_sem_init(sem_t *semaphore, int shared, unsigned int value)
{
	int error;

	init_calls++;
	if (fail_init) {
		errno = ENOSPC;
		return -1;
	}
	if (live_semaphores != 0)
		violations++;
	error = __real_sem_init(semaphore, shared, value);
	if (error == 0) {
		live_semaphore = semaphore;
		live_semaphores++;
	}
	return error;
}

int
__wrap_sem_destroy(sem_t *semaphore)
{
	int error;

	destroy_calls++;
	if (live_semaphores != 1 || semaphore != live_semaphore) {
		violations++;
		errno = EINVAL;
		return -1;
	}
	error = __real_sem_destroy(semaphore);
	if (error == 0) {
		live_semaphores--;
		live_semaphore = NULL;
	} else {
		violations++;
	}
	return error;
}

static int
check_codec(int encode, int inject_failure)
{
	const AVCodec *codec;
	AVCodecContext *context;
	int error;

	init_calls = destroy_calls = violations = 0;
	fail_init = inject_failure;
	codec = encode ? avcodec_find_encoder_by_name("hevc_v4l2m2m") :
	    avcodec_find_decoder_by_name("hevc_v4l2m2m");
	if (codec == NULL)
		return EXIT_FAILURE;
	context = avcodec_alloc_context3(codec);
	if (context == NULL)
		return EXIT_FAILURE;
	context->width = 64;
	context->height = 64;
	context->pix_fmt = AV_PIX_FMT_NV12;
	context->time_base = (AVRational){ 1, 30 };
	context->framerate = (AVRational){ 30, 1 };
	error = avcodec_open2(context, codec, NULL);
	avcodec_free_context(&context);
	if (init_calls != 1 || destroy_calls != (inject_failure ? 0U : 1U) ||
	    live_semaphores != 0 || violations != 0 ||
	    error != AVERROR(inject_failure ? ENOSPC : EINVAL)) {
		fprintf(stderr, "Semaphore lifecycle mismatch: init %u destroy %u "
		    "live %u violations %u error %d\n", init_calls, destroy_calls,
		    live_semaphores, violations, error);
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}

int
main(void)
{
	int encode, inject_failure;

	for (encode = 0; encode < 2; encode++) {
		for (inject_failure = 0; inject_failure < 2; inject_failure++) {
			if (check_codec(encode, inject_failure) != EXIT_SUCCESS)
				return EXIT_FAILURE;
		}
	}
	puts("PASS: real M2M context initializes once, checks failure and destroys only live semaphores");
	return EXIT_SUCCESS;
}
