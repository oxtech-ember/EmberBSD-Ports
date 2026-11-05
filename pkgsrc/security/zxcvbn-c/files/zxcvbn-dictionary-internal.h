/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#ifndef ZXCVBN_DICTIONARY_INTERNAL_H
#define ZXCVBN_DICTIONARY_INTERNAL_H
#include "zxcvbn-dictionary.h"

struct ZxcvbnDictionary {
	ZxcvbnDictionaryData Data;
};

static inline uint32_t
zxcvbn_dictionary_child(const ZxcvbnDictionaryData *data, size_t index)
{
	if (data->ChildWidth == 2)
		return ((const uint16_t *)data->Children)[index];
	return ((const uint32_t *)data->Children)[index];
}
#endif
