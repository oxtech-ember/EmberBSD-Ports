/*
 * SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD contributors (AI-assisted).
 *
 * This is a public API consumer. It does not copy NSS implementation code.
 */
#include <stdio.h>
#include <string.h>

#include "nss.h"
#include "pk11pub.h"
#include "secerr.h"
#include "secoidt.h"
#include "secport.h"

#define LIFECYCLES 100U

static const unsigned char sha256_abc[32] = {
	0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
	0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
	0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
	0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
};

static int
fail(unsigned int cycle, const char *operation)
{
	fprintf(stderr, "FAIL: cycle %u: %s\n", cycle, operation);
	return 1;
}

static int
run_lifecycle(unsigned int cycle)
{
	struct random_guarded_buffer {
		unsigned char before[16];
		unsigned char bytes[32];
		unsigned char after[16];
	} random_output;
	static const unsigned char input[] = "abc";
	unsigned char digest[sizeof(sha256_abc)];
	PK11SlotInfo *slot = NULL;
	const char *runtime_version;
	int failures = 0;
	unsigned int byte_index;

	if (NSS_VersionCheck("3.132") != PR_TRUE)
		return fail(cycle, "NSS_VersionCheck rejected 3.132");
	if (NSS_VersionCheck("3.133") != PR_FALSE)
		return fail(cycle, "NSS_VersionCheck accepted future version 3.133");

	runtime_version = NSS_GetVersion();
	if (runtime_version == NULL || strcmp(runtime_version, "3.132") != 0)
		return fail(cycle, "NSS_GetVersion did not report 3.132");

	if (NSS_NoDB_Init(NULL) != SECSuccess)
		return fail(cycle, "NSS_NoDB_Init(NULL) failed");

	slot = PK11_GetInternalSlot();
	if (slot == NULL) {
		failures += fail(cycle, "PK11_GetInternalSlot failed");
	} else {
		PK11_FreeSlot(slot);
		slot = NULL;
	}

	memset(digest, 0, sizeof(digest));
	if (PK11_HashBuf(SEC_OID_SHA256, digest, input, 3) != SECSuccess) {
		failures += fail(cycle, "PK11_HashBuf(SHA-256) failed");
	} else if (memcmp(digest, sha256_abc, sizeof(digest)) != 0) {
		failures += fail(cycle, "SHA-256 known-answer mismatch for abc");
	}

	memset(digest, 0xa5, sizeof(digest));
	PORT_SetError(0);
	if (PK11_HashBuf(SEC_OID_SHA256, digest, input, -1) != SECFailure ||
	    PORT_GetError() != SEC_ERROR_INVALID_ARGS) {
		failures += fail(cycle, "negative digest length was not rejected as invalid arguments");
	} else {
		for (byte_index = 0; byte_index < sizeof(digest); byte_index++) {
			if (digest[byte_index] != 0xa5) {
				failures += fail(cycle, "negative digest length changed the output buffer");
				break;
			}
		}
	}

	memset(&random_output, 0x5a, sizeof(random_output));
	if (PK11_GenerateRandom(random_output.bytes, sizeof(random_output.bytes)) != SECSuccess)
		failures += fail(cycle, "PK11_GenerateRandom failed");

	for (byte_index = 0; byte_index < sizeof(random_output.before); byte_index++) {
		if (random_output.before[byte_index] != 0x5a ||
		    random_output.after[byte_index] != 0x5a) {
			failures += fail(cycle, "PK11_GenerateRandom changed an adjacent canary");
			break;
		}
	}

	if (NSS_Shutdown() != SECSuccess)
		failures += fail(cycle, "NSS_Shutdown failed");

	return failures != 0;
}

int
main(void)
{
	unsigned int cycle;

	for (cycle = 1; cycle <= LIFECYCLES; cycle++) {
		if (run_lifecycle(cycle) != 0)
			return 1;
	}

	printf("PASS: %u NSS 3.132 no-database lifecycles; SHA-256, "
	    "invalid length, and RNG bounds checks\n", LIFECYCLES);
	return 0;
}
