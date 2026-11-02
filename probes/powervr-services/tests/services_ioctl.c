/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../adapter/errno_abi.h"
#include "../adapter/services_ioctl.h"

static unsigned int checks, failures;

#define CHECK(e) do { \
	checks++; \
	if (!(e)) { \
		fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #e); \
		failures++; \
	} \
} while (0)

#define BASE UINT64_C(0x100000000)
#define REQUEST UINT64_C(0xc0206440)

struct fixture {
	unsigned char memory[160], input[4], output[8];
	struct pvr_abi_services_command commands[2];
	struct pvr_abi_services services;
	unsigned int reads, writes, invokes;
	unsigned int fail_read;
	int operation_error, fail_write;
};

static int
read_memory(void *cookie, uint64_t address, void *out, size_t length)
{
	struct fixture *f = cookie;

	f->reads++;
	errno = EINTR;
	if (f->reads == f->fail_read || address < BASE ||
	    address - BASE > sizeof(f->memory) ||
	    length > sizeof(f->memory) - (size_t)(address - BASE))
		return EFAULT;
	memcpy(out, f->memory + (size_t)(address - BASE), length);
	return 0;
}

static int
write_memory(void *cookie, uint64_t address, const void *in, size_t length)
{
	struct fixture *f = cookie;

	f->writes++;
	errno = EINTR;
	if (address < BASE || address - BASE > sizeof(f->memory) ||
	    length > sizeof(f->memory) - (size_t)(address - BASE))
		return EFAULT;
	if (f->fail_write) {
		/* Model a checked copy that fails after a partial write. */
		if (length != 0)
			f->memory[(size_t)(address - BASE)] = *(const unsigned char *)in;
		return EFAULT;
	}
	memcpy(f->memory + (size_t)(address - BASE), in, length);
	return 0;
}

static int
invoke(void *connection, const void *input, void *output)
{
	struct fixture *f = connection;
	const unsigned char *in = input;
	unsigned char *out = output;
	size_t i;

	f->invokes++;
	errno = E2BIG;
	if (input == NULL || output == NULL) {
		CHECK(input == NULL && output == NULL);
		return f->operation_error;
	}
	for (i = 0; i < 4; i++)
		out[i] = in[i] ^ 0x5f;
	/* Synthetic payload error; this is not a transport errno. */
	out[4] = 38;
	return f->operation_error;
}

static void
put32(unsigned char *p, uint32_t value)
{
	size_t i;

	for (i = 0; i < 4; i++)
		p[i] = (unsigned char)(value >> (8 * i));
}

static void
put64(unsigned char *p, uint64_t value)
{
	size_t i;

	for (i = 0; i < 8; i++)
		p[i] = (unsigned char)(value >> (8 * i));
}

static void
reset(struct fixture *f)
{
	memset(f, 0, sizeof(*f));
	memset(f->memory, 0xcc, sizeof(f->memory));
	memset(f->output, 0xa7, sizeof(f->output));
	/* Synthetic group/function; no DDK operation is implemented. */
	put32(f->memory, 0x1234);
	put32(f->memory + 4, 0x5678);
	put64(f->memory + 8, BASE + 64);
	put64(f->memory + 16, BASE + 96);
	put32(f->memory + 24, 4);
	put32(f->memory + 28, 8);
	f->memory[64] = 0x10;
	f->memory[65] = 0x20;
	f->memory[66] = 0x30;
	f->memory[67] = 0x40;
	f->commands[0] = (struct pvr_abi_services_command) {
		0x1234, 0x5678, 4, 8, invoke
	};
	f->commands[1] = (struct pvr_abi_services_command) {
		0x1234, 0x5679, 0, 0, invoke
	};
	f->services = (struct pvr_abi_services) {
		f, f->commands, 2, f, read_memory, write_memory,
		f->input, sizeof(f->input), f->output, sizeof(f->output)
	};
}

static void
attempt(struct fixture *f, uint64_t request, uint64_t argument,
    int result, int foreign_error)
{
	errno = ERANGE;
	*pvr_abi_errno_location() = 123;
	CHECK(pvr_abi_services_ioctl(&f->services, request, argument) == result);
	CHECK(*pvr_abi_errno_location() == foreign_error);
	CHECK(errno == ERANGE);
}

static void
unchanged(const struct fixture *f, unsigned int reads)
{
	static const unsigned char expected[8] = {
		0xcc, 0xcc, 0xcc, 0xcc, 0xcc, 0xcc, 0xcc, 0xcc
	};

	CHECK(memcmp(f->memory + 96, expected, sizeof(expected)) == 0);
	CHECK(f->invokes == 0 && f->writes == 0 && f->reads == reads);
}

int
main(void)
{
	static const unsigned char expected[8] = {
		0x4f, 0x7f, 0x6f, 0x1f, 38, 0, 0, 0
	};
	struct fixture f;
	size_t i;

	reset(&f);
	attempt(&f, REQUEST, BASE, 0, 123);
	CHECK(memcmp(f.memory + 96, expected, sizeof(expected)) == 0);
	CHECK(f.invokes == 1 && f.reads == 2 && f.writes == 1);
	reset(&f);
	attempt(&f, REQUEST ^ (UINT64_C(1) << 32), BASE, -1, 25);
	unchanged(&f, 0);
	reset(&f);
	f.services.connection = NULL;
	attempt(&f, REQUEST, BASE, -1, 9);
	unchanged(&f, 0);
	reset(&f);
	f.services.read_memory = NULL;
	attempt(&f, REQUEST, BASE, -1, 22);
	unchanged(&f, 0);
	reset(&f);
	f.services.write_memory = NULL;
	attempt(&f, REQUEST, BASE, -1, 22);
	unchanged(&f, 0);
	reset(&f);
	f.services.commands = NULL;
	attempt(&f, REQUEST, BASE, -1, 22);
	unchanged(&f, 0);
	reset(&f);
	f.services.commands = NULL;
	f.services.command_count = 0;
	attempt(&f, REQUEST, BASE, -1, 25);
	unchanged(&f, 1);
	reset(&f);
	put32(f.memory, 0x4321);
	attempt(&f, REQUEST, BASE, -1, 25);
	unchanged(&f, 1);
	reset(&f);
	put32(f.memory + 4, 0x8765);
	attempt(&f, REQUEST, BASE, -1, 25);
	unchanged(&f, 1);
	reset(&f);
	f.commands[1] = f.commands[0];
	attempt(&f, REQUEST, BASE, -1, 22);
	unchanged(&f, 1);
	reset(&f);
	f.commands[0].invoke = NULL;
	attempt(&f, REQUEST, BASE, -1, 22);
	unchanged(&f, 1);
	for (i = 0; i < 2; i++) {
		reset(&f);
		put32(f.memory + 24 + 4 * i, 3);
		attempt(&f, REQUEST, BASE, -1, 22);
		unchanged(&f, 1);
		reset(&f);
		if (i == 0)
			f.services.input_capacity = 3;
		else
			f.services.output_capacity = 7;
		attempt(&f, REQUEST, BASE, -1, 22);
		unchanged(&f, 1);
		reset(&f);
		if (i == 0)
			f.services.input = NULL;
		else
			f.services.output = NULL;
		attempt(&f, REQUEST, BASE, -1, 22);
		unchanged(&f, 1);
		reset(&f);
		put64(f.memory + 8 + 8 * i, UINT64_MAX - 1);
		attempt(&f, REQUEST, BASE, -1, 14);
		unchanged(&f, 1);
		reset(&f);
		put64(f.memory + 8 + 8 * i, 0);
		attempt(&f, REQUEST, BASE, -1, 14);
		unchanged(&f, 1);
	}
	reset(&f);
	attempt(&f, REQUEST, UINT64_MAX - 30, -1, 14);
	unchanged(&f, 0);
	for (i = 1; i <= 2; i++) {
		reset(&f);
		f.fail_read = (unsigned int)i;
		attempt(&f, REQUEST, BASE, -1, 14);
		unchanged(&f, (unsigned int)i);
	}
	reset(&f);
	f.operation_error = EAGAIN;
	attempt(&f, REQUEST, BASE, -1, 11);
	CHECK(f.invokes == 1 && f.writes == 0 && f.memory[96] == 0xcc);
	reset(&f);
	f.operation_error = -1;
	attempt(&f, REQUEST, BASE, -1, 5);
	CHECK(f.invokes == 1 && f.writes == 0 && f.memory[96] == 0xcc);
	reset(&f);
	f.operation_error = 0x7fffffff;
	attempt(&f, REQUEST, BASE, -1, 5);
	CHECK(f.invokes == 1 && f.writes == 0 && f.memory[96] == 0xcc);
	reset(&f);
	f.fail_write = 1;
	attempt(&f, REQUEST, BASE, -1, 14);
	CHECK(f.invokes == 1 && f.writes == 1 && f.memory[96] == 0x4f &&
	    f.memory[97] == 0xcc);
	reset(&f);
	put32(f.memory + 4, 0x5679);
	put64(f.memory + 8, 0);
	put64(f.memory + 16, 0);
	put32(f.memory + 24, 0);
	put32(f.memory + 28, 0);
	f.services.input = NULL;
	f.services.output = NULL;
	f.services.input_capacity = 0;
	f.services.output_capacity = 0;
	attempt(&f, REQUEST, BASE, 0, 123);
	CHECK(f.invokes == 1 && f.reads == 1 && f.writes == 0);
	printf("SERVICES-IOCTL checks=%u failures=%u\n", checks, failures);
	return failures == 0 ? 0 : 65;
}
