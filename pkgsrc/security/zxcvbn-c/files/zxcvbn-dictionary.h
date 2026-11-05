/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#ifndef ZXCVBN_DICTIONARY_H
#define ZXCVBN_DICTIONARY_H

#include <stddef.h>
#include <stdint.h>
#include "zxcvbn.h"

#define ZXCVBN_DICTIONARY_ABI 1
#define ZXCVBN_DICTIONARY_CHAR_CAPACITY 128

/* A compiled dictionary, emitted by zxcvbn-dictgen.  Counts describe array
 * elements except WordEndBytes and ChildMapBytes, which describe bytes.
 * CharSetSize includes the terminating NUL.  Children contains either
 * uint16_t or uint32_t elements, selected by ChildWidth (2 or 4).
 * The caller owns these arrays and must keep them valid and immutable until
 * every dictionary handle using them has been freed.  This is not a file
 * format: the target compiler gives the arrays their native representation.
 */
typedef struct ZxcvbnDictionaryData {
	unsigned int AbiVersion;
	size_t StructSize;
	const uint32_t *Nodes;
	size_t NodeCount;
	const uint8_t *WordEnds;
	size_t WordEndBytes;
	const void *Children;
	size_t ChildCount;
	unsigned int ChildWidth;
	const uint16_t *Ranks;
	size_t RankCount;
	const uint8_t *ChildMap;
	size_t ChildMapBytes;
	size_t ChildMapWidth;
	const uint8_t *LargeCounts;
	size_t LargeCount;
	const uint8_t *SmallCounts;
	size_t SmallCount;
	const char *CharSet;
	size_t CharSetSize;
	uint32_t Root;
} ZxcvbnDictionaryData;

typedef struct ZxcvbnDictionary ZxcvbnDictionary;

#ifdef __cplusplus
extern "C" {
#endif

/* Validate once, then create a handle borrowing the immutable arrays.
 * NULL means invalid data (errno=EINVAL) or allocation failure (ENOMEM).
 * A handle can be used concurrently; callers must finish those calls before
 * freeing it.  Neither operation changes the default dictionary.
 */
ZxcvbnDictionary *ZxcvbnDictionaryCreate(const ZxcvbnDictionaryData *);
void ZxcvbnDictionaryFree(ZxcvbnDictionary *);

/* Same score and match-info contract as ZxcvbnMatch, with an explicit
 * dictionary.  A NULL handle/password returns -1 and clears *Info.
 */
double ZxcvbnMatchWithDictionary(const ZxcvbnDictionary *, const char *,
    const char *[], ZxcMatch_t **);

#ifdef __cplusplus
}
#endif
#endif
