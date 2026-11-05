/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>

#include "zxcvbn-dictionary-internal.h"

#define PATTERN_BITS 14
#define CHILD_BITS 18
#define PATTERN_MASK ((1U << PATTERN_BITS) - 1)

struct dictionary_frame {
	uint32_t node;
	size_t next;
	size_t end;
	uint64_t words;
};

static unsigned int
dictionary_word_end(const ZxcvbnDictionaryData *data, uint32_t node)
{
	return (data->WordEnds[node / 8] >> (node % 8)) & 1;
}

static void
dictionary_frame_init(struct dictionary_frame *frame,
    const ZxcvbnDictionaryData *data, const uint8_t *degrees, uint32_t node)
{
	uint32_t value = data->Nodes[node];

	frame->node = node;
	frame->next = value >> PATTERN_BITS;
	frame->end = frame->next + degrees[value & PATTERN_MASK];
	frame->words = dictionary_word_end(data, node);
}

/* Check every local reference before traversing the graph.  The format's
 * packed offsets bound both the input and the validation workspace.
 */
static int
dictionary_validate(const ZxcvbnDictionaryData *data)
{
	struct dictionary_frame *stack = NULL;
	uint64_t *totals = NULL;
	uint8_t *states = NULL, *degrees = NULL;
	size_t i, j, maps, chars, depth;
	int valid = 0, error = EINVAL;

	if (data == NULL || data->AbiVersion != ZXCVBN_DICTIONARY_ABI ||
	    data->StructSize != sizeof(*data) || data->Nodes == NULL ||
	    data->WordEnds == NULL || data->Children == NULL ||
	    data->Ranks == NULL || data->ChildMap == NULL ||
	    data->SmallCounts == NULL || data->CharSet == NULL ||
	    (data->LargeCount != 0 && data->LargeCounts == NULL) ||
	    data->NodeCount < 2 || data->ChildCount == 0 ||
	    data->ChildCount > (1U << CHILD_BITS) ||
	    data->NodeCount > data->ChildCount + 1 ||
	    data->Root >= data->NodeCount ||
	    (data->ChildWidth != 2 && data->ChildWidth != 4) ||
	    data->RankCount < 2 || data->RankCount > INT_MAX ||
	    data->SmallCount != data->NodeCount ||
	    data->LargeCount > data->NodeCount ||
	    data->WordEndBytes != (data->NodeCount + 7) / 8 ||
	    data->CharSetSize < 2 ||
	    data->CharSetSize > ZXCVBN_DICTIONARY_CHAR_CAPACITY)
		goto out;
	chars = data->CharSetSize - 1;
	if (data->CharSet[chars] != '\0' ||
	    data->ChildMapWidth != (chars + 7) / 8 ||
	    data->ChildMapBytes == 0 ||
	    data->ChildMapBytes % data->ChildMapWidth != 0)
		goto out;
	maps = data->ChildMapBytes / data->ChildMapWidth;
	if (maps > (1U << PATTERN_BITS) ||
	    dictionary_word_end(data, data->Root) != 0)
		goto out;
	for (i = 0; i < chars; i++) {
		unsigned char value = (unsigned char)data->CharSet[i];
		if (value == 0 || value >= 128 ||
		    (i != 0 && value <= (unsigned char)data->CharSet[i - 1]))
			goto out;
	}
	for (i = 1; i < data->RankCount; i++) {
		if (data->Ranks[i] == 0)
			goto out;
	}
	degrees = (uint8_t *)calloc(maps, sizeof(*degrees));
	if (degrees == NULL) {
		error = ENOMEM;
		goto out;
	}
	for (i = 0; i < maps; i++) {
		const uint8_t *row = data->ChildMap + i * data->ChildMapWidth;
		for (j = 0; j < data->ChildMapWidth * 8; j++) {
			if ((row[j / 8] & (1U << (j % 8))) == 0)
				continue;
			if (j >= chars)
				goto out;
			degrees[i]++;
		}
	}
	for (i = 0; i < data->NodeCount; i++) {
		uint32_t node = data->Nodes[i];
		size_t pattern = node & PATTERN_MASK;
		size_t first = node >> PATTERN_BITS;
		if (pattern >= maps || first > data->ChildCount ||
		    degrees[pattern] > data->ChildCount - first)
			goto out;
		for (j = first; j < first + degrees[pattern]; j++) {
			if (zxcvbn_dictionary_child(data, j) >= data->NodeCount)
				goto out;
		}
	}
	states = (uint8_t *)calloc(data->NodeCount, sizeof(*states));
	totals = (uint64_t *)calloc(data->NodeCount, sizeof(*totals));
	stack = (struct dictionary_frame *)calloc(data->NodeCount,
	    sizeof(*stack));
	if (states == NULL || totals == NULL || stack == NULL) {
		error = ENOMEM;
		goto out;
	}
	depth = 1;
	states[data->Root] = 1;
	dictionary_frame_init(&stack[0], data, degrees, data->Root);
	while (depth != 0) {
		struct dictionary_frame *frame = &stack[depth - 1];
		if (frame->next < frame->end) {
			uint32_t child = zxcvbn_dictionary_child(data, frame->next);
			if (states[child] == 1)
				goto out;
			if (states[child] == 0) {
				if (depth == data->NodeCount)
					goto out;
				states[child] = 1;
				dictionary_frame_init(&stack[depth++], data,
				    degrees, child);
				continue;
			}
			frame->words += totals[child];
			frame->next++;
			if (frame->words >= data->RankCount)
				goto out;
			continue;
		}
		/* The root's truncated 16-bit count is never read by the scorer.
		 * Every other reachable node's count advances dictionary ranks.
		 */
		if (frame->node != data->Root) {
			uint32_t stored = data->SmallCounts[frame->node];
			if (frame->node < data->LargeCount)
				stored += (uint32_t)data->LargeCounts[frame->node] * 256;
			if (frame->words != stored)
				goto out;
		}
		totals[frame->node] = frame->words;
		states[frame->node] = 2;
		depth--;
	}
	valid = totals[data->Root] == data->RankCount - 1;
out:
	free(stack);
	free(totals);
	free(states);
	free(degrees);
	if (!valid)
		errno = error;
	return valid;
}

ZxcvbnDictionary *
ZxcvbnDictionaryCreate(const ZxcvbnDictionaryData *data)
{
	ZxcvbnDictionary *dictionary;

	if (!dictionary_validate(data))
		return NULL;
	dictionary = (ZxcvbnDictionary *)malloc(sizeof(*dictionary));
	if (dictionary == NULL) {
		errno = ENOMEM;
		return NULL;
	}
	dictionary->Data = *data;
	return dictionary;
}

void
ZxcvbnDictionaryFree(ZxcvbnDictionary *dictionary)
{
	free(dictionary);
}
