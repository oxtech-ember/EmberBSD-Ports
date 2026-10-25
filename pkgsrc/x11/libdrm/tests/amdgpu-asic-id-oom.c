/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD; verify the ASIC-ID path allocation failure fallback. */

#define _GNU_SOURCE

#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

#define AMDGPU_ASIC_ID_TABLE "/usr/pkg/share/libdrm/amdgpu.ids"
#define AMDGPU_IDS_FLAGS_FUSION 0x1
#define HAVE_SECURE_GETENV 0

struct amdgpu_info {
	uint32_t ids_flags;
};

struct amdgpu_device {
	struct amdgpu_info info;
	char *marketing_name;
};

static int parse_one_line(struct amdgpu_device *, const char *);
static void amdgpu_parse_proc_cpuinfo(struct amdgpu_device *);
static void drmMsg(const char *, ...);
static char *test_strdup(const char *);
static FILE *test_fopen(const char *, const char *);
static int test_fprintf(FILE *, const char *, ...);
static void test_free(void *);

static unsigned int strdup_calls;
static unsigned int fopen_calls;
static unsigned int fprintf_calls;
static unsigned int oom_diagnostic_calls;
static unsigned int null_string_arguments;
static unsigned int unexpected_formats;
static unsigned int free_calls;
static unsigned int null_free_calls;
static unsigned int nonnull_free_calls;
static unsigned int cpuinfo_calls;
static unsigned int wrong_strdup_path;
static unsigned int null_fopen_path;

static int
parse_one_line(struct amdgpu_device *dev, const char *line)
{
	(void)dev;
	(void)line;
	return -EAGAIN;
}

static void
amdgpu_parse_proc_cpuinfo(struct amdgpu_device *dev)
{
	(void)dev;
	cpuinfo_calls++;
}

static void
drmMsg(const char *format, ...)
{
	(void)format;
}

static char *
test_strdup(const char *path)
{
	strdup_calls++;
	if (strcmp(path, AMDGPU_ASIC_ID_TABLE) != 0)
		wrong_strdup_path++;
	return NULL;
}

static FILE *
test_fopen(const char *path, const char *mode)
{
	(void)mode;
	fopen_calls++;
	if (path == NULL)
		null_fopen_path++;
	return NULL;
}

static int
test_fprintf(FILE *stream, const char *format, ...)
{
	va_list ap;
	char *first_string;

	(void)stream;
	fprintf_calls++;
	if (strcmp(format, "Cannot allocate ASIC ID table path\n") == 0) {
		oom_diagnostic_calls++;
	} else if (strcmp(format, "%s: %s\n") == 0) {
		va_start(ap, format);
		first_string = va_arg(ap, char *);
		if (first_string == NULL)
			null_string_arguments++;
		(void)va_arg(ap, char *);
		va_end(ap);
	} else {
		unexpected_formats++;
	}
	return 0;
}

static void
test_free(void *pointer)
{
	free_calls++;
	if (pointer == NULL)
		null_free_calls++;
	else {
		nonnull_free_calls++;
		free(pointer);
	}
}

#define strdup test_strdup
#define fopen test_fopen
#define fprintf test_fprintf
#define free test_free
#include "amdgpu_parse_asic_ids.inc"
#undef free
#undef fprintf
#undef fopen
#undef strdup

static void
reset_counts(void)
{
	strdup_calls = 0;
	fopen_calls = 0;
	fprintf_calls = 0;
	oom_diagnostic_calls = 0;
	null_string_arguments = 0;
	unexpected_formats = 0;
	free_calls = 0;
	null_free_calls = 0;
	nonnull_free_calls = 0;
	cpuinfo_calls = 0;
	wrong_strdup_path = 0;
	null_fopen_path = 0;
}

static int
check_case(const char *name, uint32_t ids_flags,
    unsigned int expected_cpuinfo_calls)
{
	struct amdgpu_device dev = { { ids_flags }, NULL };

	reset_counts();
	amdgpu_parse_asic_ids(&dev);
	if (strdup_calls != 1 || wrong_strdup_path != 0) {
		fprintf(stderr, "FAIL: %s: wrong strdup call or path\n", name);
		return 1;
	}
	if (fopen_calls != 0 || null_fopen_path != 0) {
		fprintf(stderr, "FAIL: %s: fopen received the failed path\n", name);
		return 1;
	}
	if (fprintf_calls != 1 || oom_diagnostic_calls != 1 ||
	    null_string_arguments != 0 || unexpected_formats != 0) {
		fprintf(stderr, "FAIL: %s: invalid OOM diagnostic arguments\n", name);
		return 1;
	}
	if (free_calls != 1 || null_free_calls != 1 ||
	    nonnull_free_calls != 0) {
		fprintf(stderr, "FAIL: %s: allocation cleanup differs\n", name);
		return 1;
	}
	if (cpuinfo_calls != expected_cpuinfo_calls) {
		fprintf(stderr, "FAIL: %s: CPU fallback count %u, expected %u\n",
		    name, cpuinfo_calls, expected_cpuinfo_calls);
		return 1;
	}
	printf("PASS: %s\n", name);
	return 0;
}

int
main(void)
{
	int failures = 0;

	failures += check_case("oom-preserves-fusion-cpu-fallback",
	    AMDGPU_IDS_FLAGS_FUSION, 1);
	failures += check_case("oom-skips-non-fusion-cpu-fallback", 0, 0);
	return failures != 0;
}
