/* SPDX-License-Identifier: BSD-2-Clause */
/* Test early KWAJ cleanup through the public mspack_system contract. */
#include <sys/types.h>

#include <mspack.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "kwaj-inputs.h"

#define ALLOC_SLOTS 64

struct input_file {
	struct mspack_file base;
	const unsigned char *bytes;
	size_t length;
	size_t offset;
	int opened;
};

static struct input_file input;
static void *allocations[ALLOC_SLOTS];
static unsigned int invalid_frees;
static unsigned int callback_errors;

static struct mspack_file *
input_open(struct mspack_system *sys, const char *name, int mode)
{
	(void)sys;
	if (strcmp(name, "input") != 0 || mode != MSPACK_SYS_OPEN_READ ||
	    input.opened) {
		callback_errors++;
		return NULL;
	}
	input.offset = 0;
	input.opened = 1;
	return &input.base;
}

static void
input_close(struct mspack_file *file)
{
	if (file != &input.base || !input.opened) {
		callback_errors++;
		return;
	}
	input.opened = 0;
}

static int
input_read(struct mspack_file *file, void *buffer, int count)
{
	size_t available, take;

	if (file != &input.base || !input.opened || count < 0) {
		callback_errors++;
		return -1;
	}
	available = input.length - input.offset;
	take = (size_t)count < available ? (size_t)count : available;
	if (take != 0)
		memcpy(buffer, input.bytes + input.offset, take);
	input.offset += take;
	return (int)take;
}

static int
input_write(struct mspack_file *file, void *buffer, int count)
{
	(void)file;
	(void)buffer;
	(void)count;
	callback_errors++;
	return -1;
}

static int
input_seek(struct mspack_file *file, off_t offset, int mode)
{
	off_t base, length;

	if (file != &input.base || !input.opened) {
		callback_errors++;
		return -1;
	}
	length = (off_t)input.length;
	switch (mode) {
	case MSPACK_SYS_SEEK_START:
		base = 0;
		break;
	case MSPACK_SYS_SEEK_CUR:
		base = (off_t)input.offset;
		break;
	case MSPACK_SYS_SEEK_END:
		base = length;
		break;
	default:
		callback_errors++;
		return -1;
	}
	if (offset < -base || offset > length - base)
		return -1;
	input.offset = (size_t)(base + offset);
	return 0;
}

static off_t
input_tell(struct mspack_file *file)
{
	if (file != &input.base || !input.opened) {
		callback_errors++;
		return -1;
	}
	return (off_t)input.offset;
}

static void
input_message(struct mspack_file *file, const char *format, ...)
{
	(void)file;
	(void)format;
}

static void *
poison_alloc(struct mspack_system *sys, size_t size)
{
	void *p;
	size_t slot;

	(void)sys;
	for (slot = 0; slot < ALLOC_SLOTS; slot++)
		if (allocations[slot] == NULL)
			break;
	if (slot == ALLOC_SLOTS) {
		callback_errors++;
		return NULL;
	}
	p = malloc(size != 0 ? size : 1);
	if (p != NULL) {
		memset(p, 0xa5, size);
		allocations[slot] = p;
	}
	return p;
}

static void
owned_free(void *p)
{
	size_t slot;

	if (p == NULL)
		return;
	for (slot = 0; slot < ALLOC_SLOTS; slot++) {
		if (allocations[slot] == p) {
			allocations[slot] = NULL;
			free(p);
			return;
		}
	}
	/* Count invalid requests without passing a poisoned pointer to free(). */
	invalid_frees++;
}

static void
input_copy(void *src, void *dest, size_t size)
{
	if (size != 0)
		memcpy(dest, src, size);
}

static struct mspack_system system_callbacks = {
	input_open, input_close, input_read, input_write, input_seek,
	input_tell, input_message, poison_alloc, owned_free, input_copy, NULL
};

static int
run_case(const char *name, const unsigned char *bytes, size_t length,
    int expected_error)
{
	struct mskwaj_decompressor *decoder;
	struct mskwajd_header *header;
	unsigned int live = 0;
	size_t slot;
	int observed_error, shape_ok, passed;

	invalid_frees = 0;
	callback_errors = 0;
	input.bytes = bytes;
	input.length = length;
	input.offset = 0;
	input.opened = 0;
	decoder = mspack_create_kwaj_decompressor(&system_callbacks);
	if (decoder == NULL) {
		fprintf(stderr, "case=%s constructor=FAIL\n", name);
		return 0;
	}
	header = decoder->open(decoder, "input");
	observed_error = decoder->last_error(decoder);
	shape_ok = expected_error == MSPACK_ERR_OK ? header != NULL :
	    header == NULL;
	if (header != NULL) {
		shape_ok = shape_ok && header->comp_type == MSKWAJ_COMP_NONE &&
		    header->data_offset == 14 && header->headers == 0 &&
		    header->length == 0 && header->filename == NULL &&
		    header->extra == NULL && header->extra_length == 0;
		decoder->close(decoder, header);
	}
	mspack_destroy_kwaj_decompressor(decoder);
	for (slot = 0; slot < ALLOC_SLOTS; slot++)
		if (allocations[slot] != NULL)
			live++;
	passed = observed_error == expected_error && shape_ok &&
	    invalid_frees == 0 && callback_errors == 0 && live == 0 &&
	    input.opened == 0;
	printf("case=%s error=%d expected=%d shape=%d invalid_frees=%u "
	    "callback_errors=%u live=%u open=%d result=%s\n", name,
	    observed_error, expected_error, shape_ok, invalid_frees,
	    callback_errors, live, input.opened, passed ? "PASS" : "FAIL");
	/* A failed case must not contaminate the next diagnostic case. */
	for (slot = 0; slot < ALLOC_SLOTS; slot++) {
		free(allocations[slot]);
		allocations[slot] = NULL;
	}
	return passed;
}

int
main(void)
{
	int selftest, passed = 0;

	MSPACK_SYS_SELFTEST(selftest);
	if (selftest != MSPACK_ERR_OK) {
		fprintf(stderr, "ABI selftest failed: %d\n", selftest);
		return 2;
	}
	passed += run_case("empty", kwaj_blank, 0, MSPACK_ERR_READ);
	passed += run_case("blank", kwaj_blank, sizeof(kwaj_blank),
	    MSPACK_ERR_SIGNATURE);
	passed += run_case("valid-f00", kwaj_f00, sizeof(kwaj_f00),
	    MSPACK_ERR_OK);
	printf("cases=%d/3\n", passed);
	return passed == 3 ? 0 : 1;
}
