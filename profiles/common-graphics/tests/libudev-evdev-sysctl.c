/* SPDX-License-Identifier: BSD-2-Clause */
/* Exercise the real cache with a controlled sysctl syscall boundary. */
#include <errno.h>
#include <stdio.h>
#define sysctlbyname test_sysctlbyname
#include "udev-utils.c"
#undef sysctlbyname
#include "libudev-contract-stubs.h"

static const char *scenario;
static unsigned int calls;
static int invalid_length;

int
test_sysctlbyname(const char *name, void *oldp, size_t *oldlenp,
    const void *newp, size_t newlen)
{
	int value;

	calls++;
	if (strcmp(name, "kern.features.evdev_support") != 0 ||
	    oldp == NULL || oldlenp == NULL || newp != NULL || newlen != 0)
		abort();
	if (*oldlenp != sizeof(value)) {
		invalid_length = 1;
		errno = EINVAL;
		return (-1);
	}
	value = strcmp(scenario, "present") == 0 ? 1 : 0;
	if (strcmp(scenario, "nonzero") == 0)
		value = 2;
	if (calls == 1 && (strcmp(scenario, "error") == 0 ||
	    strcmp(scenario, "short") == 0 || strcmp(scenario, "oversize") == 0)) {
		value = 1;
		memcpy(oldp, &value, sizeof(value));
		*oldlenp = strcmp(scenario, "oversize") == 0 ?
		    sizeof(value) + 1 : sizeof(value) - 1;
		if (strcmp(scenario, "error") == 0) {
			errno = ENOMEM;
			return (-1);
		}
		return (0);
	}
	memcpy(oldp, &value, sizeof(value));
	*oldlenp = sizeof(value);
	return (0);
}

int
main(int argc, char **argv)
{
	int expected, value;
	unsigned int expected_calls;

	if (argc != 2)
		return (2);
	scenario = argv[1];
	if (strcmp(scenario, "present") != 0 &&
	    strcmp(scenario, "nonzero") != 0 && strcmp(scenario, "absent") != 0 &&
	    strcmp(scenario, "error") != 0 && strcmp(scenario, "short") != 0 &&
	    strcmp(scenario, "oversize") != 0)
		return (2);
	expected = strcmp(scenario, "present") == 0 ||
	    strcmp(scenario, "nonzero") == 0;
	expected_calls = strcmp(scenario, "error") == 0 ||
	    strcmp(scenario, "short") == 0 || strcmp(scenario, "oversize") == 0 ? 2 : 1;
	value = kernel_has_evdev_enabled();
	if (invalid_length) {
		fprintf(stderr, "FAIL: uninitialized sysctl buffer length\n");
		return (1);
	}
	if (value != expected) {
		fprintf(stderr, "FAIL: incomplete sysctl result accepted\n");
		return (1);
	}
	if (kernel_has_evdev_enabled() != expected ||
	    kernel_has_evdev_enabled() != expected || calls != expected_calls) {
		fprintf(stderr, "FAIL: failed sysctl populated cache or valid result not cached\n");
		return (1);
	}
	printf("PASS %s calls=%u\n", scenario, calls);
	return (0);
}
