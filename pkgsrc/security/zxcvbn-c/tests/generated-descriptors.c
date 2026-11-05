/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#include <stdio.h>
#include <zxcvbn-dictionary.h>
extern const ZxcvbnDictionaryData SixWordLists;
extern const ZxcvbnDictionaryData SmallWordList;
int main(void)
{
    const ZxcvbnDictionaryData *data[] = { &SixWordLists, &SmallWordList };
    for (unsigned i = 0; i < 2; ++i) {
        ZxcvbnDictionary *dictionary = ZxcvbnDictionaryCreate(data[i]);
        if (!dictionary) { perror("ZxcvbnDictionaryCreate"); return 1; }
        if (data[i]->ChildWidth != (i ? 2U : 4U)) return 2;
        if (ZxcvbnMatchWithDictionary(dictionary, "password", NULL, NULL) < 0) return 3;
        ZxcvbnDictionaryFree(dictionary);
    }
    puts("PASS: generated 16-bit and 32-bit descriptors");
    return 0;
}
