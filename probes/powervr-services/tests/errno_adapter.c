/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <stdio.h>
#include <unistd.h>

#include "../adapter/errno_abi.h"

struct result {
	unsigned int checks;
	unsigned int failures;
};

struct worker {
	const int *main_slot;
	struct result result;
};

static void
check(struct result *result, int condition, const char *name)
{
	result->checks++;
	if (!condition) {
		fprintf(stderr, "FAIL: %s\n", name);
		result->failures++;
	}
}

static void *
worker(void *arg)
{
	struct worker *state = arg;
	const int *slot;
	int saved;
	int status;

	errno = ERANGE;
	slot = pvr_abi_errno_location();
	saved = errno;
	check(&state->result, saved == ERANGE, "worker accessor keeps native errno");
	check(&state->result, slot != &errno, "worker has a foreign errno slot");
	check(&state->result, slot != state->main_slot, "threads have distinct slots");
	check(&state->result, *slot == 0, "new thread foreign errno starts at zero");
	errno = ERANGE;
	status = pvr_abi_errno_set_native(EDEADLK);
	saved = errno;
	check(&state->result, status == 0 && *slot == 35,
	    "worker stores Linux EDEADLK");
	check(&state->result, saved == ERANGE, "worker setter keeps native errno");
	check(&state->result, slot == pvr_abi_errno_location(), "worker slot is stable");
	return NULL;
}

int
main(void)
{
	/* Literal Linux ABI results, independently checked against the pinned UAPI. */
	static const struct {
		int native;
		int linux_error;
	} cases[] = {
		{0, 0},
#include "errno_cases.inc"
	};
	static const int unsupported[] = {
		-1, INT_MIN, INT_MAX,
#ifdef __NetBSD__
		EPROCLIM, EBADRPC, ERPCMISMATCH, EPROGUNAVAIL,
		EPROGMISMATCH, EPROCUNAVAIL, EFTYPE, EAUTH, ENEEDAUTH, ENOATTR,
#endif
	};
	struct result result = {0, 0};
	struct worker state;
	pthread_t thread;
	int *slot;
	int status;
	int saved;

	if (geteuid() == 0)
		return 77;
	errno = EBUSY;
	slot = pvr_abi_errno_location();
	saved = errno;
	check(&result, saved == EBUSY, "accessor keeps native errno");
	check(&result, slot != &errno, "foreign errno does not alias native errno");
	check(&result, *slot == 0, "main foreign errno starts at zero");
	check(&result, slot == pvr_abi_errno_location(), "main slot is stable");

	for (unsigned int i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
		*slot = 171;
		errno = EBUSY;
		status = pvr_abi_errno_from_native(cases[i].native);
		saved = errno;
		check(&result, status == cases[i].linux_error, "semantic error translation");
		check(&result, saved == EBUSY, "translation keeps native errno");
		check(&result, *pvr_abi_errno_location() == 171,
		    "translation keeps foreign errno");
		errno = EBUSY;
		status = pvr_abi_errno_set_native(cases[i].native);
		saved = errno;
		check(&result, status == 0 && *slot == cases[i].linux_error,
		    "setter stores the translated error");
		check(&result, saved == EBUSY, "setter keeps native errno");
	}
	for (unsigned int i = 0; i < sizeof(unsupported) / sizeof(unsupported[0]); i++) {
		*slot = 171;
		errno = EBUSY;
		status = pvr_abi_errno_from_native(unsupported[i]);
		saved = errno;
		check(&result, status == -1, "unknown error is not guessed");
		check(&result, saved == EBUSY, "unknown translation keeps native errno");
		errno = EBUSY;
		status = pvr_abi_errno_set_native(unsupported[i]);
		saved = errno;
		check(&result, status == -1 && *pvr_abi_errno_location() == 171,
		    "unknown setter retains foreign state");
		check(&result, saved == EBUSY, "unknown setter keeps native errno");
	}
	status = pvr_abi_errno_set_native(EAGAIN);
	check(&result, status == 0 && *slot == 11, "main stores Linux EAGAIN");
	state = (struct worker){slot, {0, 0}};
	if (pthread_create(&thread, NULL, worker, &state) != 0)
		return 73;
	if (pthread_join(thread, NULL) != 0)
		_exit(73);
	result.checks += state.result.checks;
	result.failures += state.result.failures;
	check(&result, *slot == 11, "worker cannot overwrite main foreign errno");
	status = pvr_abi_errno_set_native(0);
	check(&result, status == 0 && *slot == 0, "explicit zero clears foreign errno");
	printf("ERRNO checks=%u failures=%u native_EAGAIN=%d linux_EAGAIN=11\n",
	    result.checks, result.failures, EAGAIN);
	return result.failures == 0 ? 0 : 65;
}
