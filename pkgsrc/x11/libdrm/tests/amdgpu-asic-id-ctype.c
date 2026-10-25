/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD; execute the actual libdrm parser in a focused fixture. */

#define _GNU_SOURCE

#include <ctype.h>
#include <errno.h>
#include <locale.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct amdgpu_info {
	uint32_t asic_id;
	uint32_t pci_rev_id;
};

struct amdgpu_device {
	struct amdgpu_info info;
	char *marketing_name;
};

#include "parse_one_line.inc"

static int
check_case(const char *name, const char *line, int expected_result,
    const char *expected_name)
{
	struct amdgpu_device dev = { { 0x1002, 0 }, NULL };
	int result;

	result = parse_one_line(&dev, line);
	if (result != expected_result) {
		fprintf(stderr, "FAIL: %s: result %d, expected %d\n",
		    name, result, expected_result);
		free(dev.marketing_name);
		return 1;
	}
	if (expected_name != NULL &&
	    (dev.marketing_name == NULL ||
	    strcmp(dev.marketing_name, expected_name) != 0)) {
		fprintf(stderr, "FAIL: %s: parsed name differs\n", name);
		free(dev.marketing_name);
		return 1;
	}
	if (expected_name == NULL && dev.marketing_name != NULL) {
		fprintf(stderr, "FAIL: %s: unexpected parsed name\n", name);
		free(dev.marketing_name);
		return 1;
	}
	free(dev.marketing_name);
	printf("PASS: %s\n", name);
	return 0;
}

int
main(void)
{
	int failed = 0;

	if (setlocale(LC_CTYPE, "C") == NULL) {
		fprintf(stderr, "FAIL: cannot select the C character locale\n");
		return 1;
	}
	failed += check_case("trim-space-and-tab", "1002,0, \tRadeon", 0,
	    "Radeon");
	failed += check_case("preserve-high-bit-name-byte",
	    "1002,0, \t\377GPU", 0, "\377GPU");
	failed += check_case("preserve-vertical-tab", "1002,0,\vRadeon", 0,
	    "\vRadeon");
	failed += check_case("reject-space-and-tab-only-name", "1002,0, \t",
	    -EINVAL, NULL);
	return failed != 0;
}
