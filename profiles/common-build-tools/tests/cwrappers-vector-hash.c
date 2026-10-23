/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
/* Origin: EmberBSD (AI-assisted). Test the unchanged three-word hash API. */
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void mi_vector_hash(const void *, size_t, uint32_t, uint32_t[3]);

int
main(int argc, char **argv)
{
	static const size_t large[] = { 257, 511, 512, 1023, 4095, 4096, 4097 };
	static const uint32_t seeds[] = { 0, 1, 0xdeadbeef, UINT32_MAX };
	uint32_t expected[3], actual[3];
	uint8_t *reference, *storage, *key;
	size_t index, len, off, seed, i, padding, size;
	int vectors;

	if (argc != 2 || (strcmp(argv[1], "--vectors") != 0 &&
	    strcmp(argv[1], "--exact") != 0)) {
		fprintf(stderr, "usage: %s --vectors|--exact\n", argv[0]);
		return 2;
	}
	vectors = strcmp(argv[1], "--vectors") == 0;
	padding = vectors ? 16 : 0;
	for (index = 0; index < 256 + sizeof(large) / sizeof(large[0]); ++index) {
		len = index < 256 ? index : large[index - 256];
		/* malloc alignment plus one selects the upstream bytewise route. */
		reference = malloc(len + 1);
		if (reference == NULL)
			return 3;
		for (seed = 0; seed < sizeof(seeds) / sizeof(seeds[0]); ++seed) {
			for (i = 0; i < len; ++i)
				reference[i + 1] = (uint8_t)(i * 37 + len + seeds[seed]);
			mi_vector_hash(reference + 1, len, seeds[seed], expected);
			for (off = 0; off < 16; ++off) {
				size = len + off + padding;
				storage = malloc(size != 0 ? size : 1);
				if (storage == NULL) {
					free(reference);
					return 3;
				}
				memset(storage, 0xa5, size != 0 ? size : 1);
				key = storage + off;
				memcpy(key, reference + 1, len);
				mi_vector_hash(key, len, seeds[seed], actual);
				if (memcmp(expected, actual, sizeof(actual)) != 0) {
					fprintf(stderr, "hash mismatch: len=%zu off=%zu seed=%" PRIu32 "\n",
					    len, off, seeds[seed]);
					free(storage);
					free(reference);
					return 1;
				}
				if (vectors)
					printf("%zu %zu %08" PRIx32 " %08" PRIx32 " %08" PRIx32 " %08" PRIx32 "\n",
					    len, off, seeds[seed], actual[0], actual[1], actual[2]);
				free(storage);
			}
		}
		free(reference);
	}
	return 0;
}
