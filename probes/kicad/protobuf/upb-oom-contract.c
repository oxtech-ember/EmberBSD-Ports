/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. Prepared with AI assistance. */
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include "google/protobuf/descriptor.upb_minitable.h"
#include "upb/mem/arena.h"
#include "upb/message/accessors.h"
#include "upb/message/array.h"
#include "upb/message/copy.h"
#include "upb/message/message.h"
#include "upb/mini_table/message.h"

static unsigned allocation_attempts;

/* This allocator never owns heap memory, including during arena creation. */
static void *
refuse_allocation(upb_alloc *allocator, void *pointer, size_t old_size,
    size_t size, size_t *actual_size)
{

	(void)allocator;
	(void)pointer;
	(void)old_size;
	(void)actual_size;
	if (size != 0)
		++allocation_attempts;
	return NULL;
}

static int
exhausted_message_clone(void)
{
	int result = 1;
	upb_Arena *source_arena = upb_Arena_New();
	upb_Arena *normal_arena = upb_Arena_New();
	upb_Arena *exhausted_arena = NULL;
	union {
		max_align_t alignment;
		unsigned char bytes[512];
	} initial;
	upb_alloc allocator = {refuse_allocation};
	const upb_MiniTable *table = &google__protobuf__DescriptorProto_msg_init;
	upb_Message *source, *normal, *failed;
	unsigned before_clone;

	if (!source_arena || !normal_arena)
		goto cleanup;
	source = upb_Message_New(table, source_arena);
	if (!source)
		goto cleanup;
	normal = upb_Message_DeepClone(source, table, normal_arena);
	if (!normal || normal == source)
		goto cleanup;
	exhausted_arena = upb_Arena_Init(initial.bytes, sizeof(initial.bytes),
	    &allocator);
	if (!exhausted_arena)
		goto cleanup;
	while (upb_Arena_Malloc(exhausted_arena, 16) != NULL)
		continue;
	before_clone = allocation_attempts;
	puts("Cloning into a valid exhausted arena");
	fflush(stdout);
	failed = upb_Message_DeepClone(source, table, exhausted_arena);
	if (failed != NULL || allocation_attempts <= before_clone)
		goto cleanup;
	/* Allocation failure must leave the source usable. */
	if (!upb_Message_DeepClone(source, table, normal_arena))
		goto cleanup;
	puts("PASS: UPB clone allocation failure returns NULL and preserves source");
	result = 0;
cleanup:
	if (exhausted_arena)
		upb_Arena_Free(exhausted_arena);
	if (normal_arena)
		upb_Arena_Free(normal_arena);
	if (source_arena)
		upb_Arena_Free(source_arena);
	if (result != 0)
		fputs("FAIL: UPB allocation failure contract\n", stderr);
	return result;
}

static int
has_name(const upb_Message *message, const upb_MiniTableField *field)
{
	const upb_Array *array = upb_Message_GetArray(message, field);
	upb_StringView value;

	if (!array || upb_Array_Size(array) != 1)
		return 0;
	value = upb_Array_Get(array, 0).str_val;
	return value.size == 5 && memcmp(value.data, "KiCad", 5) == 0;
}

static int
exhausted_array_clone(void)
{
	int result = 1;
	upb_Arena *source_arena = upb_Arena_New();
	upb_Arena *normal_arena = upb_Arena_New();
	upb_Arena *limited_arena = NULL;
	union {
		max_align_t alignment;
		unsigned char bytes[512];
	} initial;
	upb_alloc allocator = {refuse_allocation};
	const upb_MiniTable *table = &google__protobuf__DescriptorProto_msg_init;
	const upb_MiniTableField *field;
	upb_Message *source, *normal, *failed;
	upb_Array *array;
	upb_MessageValue value;
	size_t padding = 0;
	unsigned before_clone;

	if (!source_arena || !normal_arena)
		goto cleanup;
	field = upb_MiniTable_FindFieldByNumber(table, 10); /* reserved_name */
	if (!field || upb_MiniTableField_CType(field) != kUpb_CType_String)
		goto cleanup;
	source = upb_Message_New(table, source_arena);
	if (!source)
		goto cleanup;
	array = upb_Message_GetOrCreateMutableArray(source, field, source_arena);
	if (!array)
		goto cleanup;
	value.str_val = upb_StringView_FromString("KiCad");
	if (!upb_Array_Append(array, value, source_arena))
		goto cleanup;
	normal = upb_Message_DeepClone(source, table, normal_arena);
	if (!normal || !has_name(normal, field))
		goto cleanup;

	/* Measure the space left after a message allocation, using public APIs. */
	limited_arena = upb_Arena_Init(initial.bytes, sizeof(initial.bytes),
	    &allocator);
	if (!limited_arena || !upb_Message_New(table, limited_arena))
		goto cleanup;
	while (upb_Arena_Malloc(limited_arena, 16) != NULL)
		padding += 16;
	if (padding == 0)
		goto cleanup;
	upb_Arena_Free(limited_arena);
	limited_arena = upb_Arena_Init(initial.bytes, sizeof(initial.bytes),
	    &allocator);
	if (!limited_arena || !upb_Arena_Malloc(limited_arena, padding))
		goto cleanup;
	/* A message still fits, but the following array allocation must fail. */
	before_clone = allocation_attempts;
	failed = upb_Message_DeepClone(source, table, limited_arena);
	if (allocation_attempts <= before_clone)
		goto cleanup;
	if (failed != NULL) {
		if (!upb_Message_GetArray(failed, field))
			fputs("FAIL: clone reports success after array allocation "
			    "failure; repeated field is absent\n", stderr);
		goto cleanup;
	}
	if (!has_name(source, field))
		goto cleanup;
	normal = upb_Message_DeepClone(source, table, normal_arena);
	if (!normal || !has_name(normal, field))
		goto cleanup;
	puts("PASS: UPB array allocation failure propagates and preserves source");
	result = 0;
cleanup:
	if (limited_arena)
		upb_Arena_Free(limited_arena);
	if (normal_arena)
		upb_Arena_Free(normal_arena);
	if (source_arena)
		upb_Arena_Free(source_arena);
	if (result != 0)
		fputs("FAIL: UPB array allocation failure contract\n", stderr);
	return result;
}

static const char scalar_text[] =
    "KiCad scalar string allocation must report failure without losing data";

static int
has_scalar_text(const upb_Message *message, const upb_MiniTableField *field)
{
	upb_StringView value = upb_Message_GetString(message, field,
	    upb_StringView_FromDataAndSize(NULL, 0));

	return value.size == sizeof(scalar_text) - 1 &&
	    memcmp(value.data, scalar_text, value.size) == 0;
}

static int
exhausted_string_clone(int copy_into_existing)
{
	int result = 1;
	upb_Arena *source_arena = upb_Arena_New();
	upb_Arena *normal_arena = upb_Arena_New();
	upb_Arena *limited_arena = NULL;
	union {
		max_align_t alignment;
		unsigned char bytes[512];
	} initial;
	upb_alloc allocator = {refuse_allocation};
	const upb_MiniTable *table = &google__protobuf__DescriptorProto_msg_init;
	const upb_MiniTableField *field;
	upb_Message *source, *normal, *destination;
	size_t padding = 0;
	unsigned before_copy;

	if (!source_arena || !normal_arena)
		goto cleanup;
	field = upb_MiniTable_FindFieldByNumber(table, 1); /* name */
	if (!field || upb_MiniTableField_CType(field) != kUpb_CType_String)
		goto cleanup;
	source = upb_Message_New(table, source_arena);
	if (!source || !upb_Message_SetString(source, field,
	    upb_StringView_FromString(scalar_text), source_arena))
		goto cleanup;
	normal = upb_Message_DeepClone(source, table, normal_arena);
	if (!normal || !has_scalar_text(normal, field))
		goto cleanup;
	limited_arena = upb_Arena_Init(initial.bytes, sizeof(initial.bytes),
	    &allocator);
	if (!limited_arena)
		goto cleanup;
	destination = upb_Message_New(table, limited_arena);
	if (!destination)
		goto cleanup;
	while (upb_Arena_Malloc(limited_arena, 16) != NULL)
		padding += 16;
	if (padding == 0)
		goto cleanup;
	if (!copy_into_existing) {
		upb_Arena_Free(limited_arena);
		limited_arena = upb_Arena_Init(initial.bytes,
		    sizeof(initial.bytes), &allocator);
		if (!limited_arena || !upb_Arena_Malloc(limited_arena, padding))
			goto cleanup;
	}
	/* DeepClone can allocate the message, but not its scalar string. */
	before_copy = allocation_attempts;
	if (copy_into_existing) {
		if (upb_Message_DeepCopy(destination, source, table, limited_arena))
			goto cleanup;
	} else if (upb_Message_DeepClone(source, table, limited_arena) != NULL) {
		goto cleanup;
	}
	if (allocation_attempts <= before_copy || !has_scalar_text(source, field))
		goto cleanup;
	normal = upb_Message_New(table, normal_arena);
	if (!normal || !upb_Message_DeepCopy(normal, source, table, normal_arena) ||
	    !has_scalar_text(normal, field))
		goto cleanup;
	puts(copy_into_existing ?
	    "PASS: UPB scalar string DeepCopy allocation failure returns false" :
	    "PASS: UPB scalar string DeepClone allocation failure returns NULL");
	result = 0;
cleanup:
	if (limited_arena)
		upb_Arena_Free(limited_arena);
	if (normal_arena)
		upb_Arena_Free(normal_arena);
	if (source_arena)
		upb_Arena_Free(source_arena);
	if (result != 0)
		fputs("FAIL: UPB scalar string allocation failure contract\n", stderr);
	return result;
}

int
main(int argc, char **argv)
{

	if (argc == 2 && strcmp(argv[1], "--array-oom") == 0)
		return exhausted_array_clone();
	if (argc == 2 && strcmp(argv[1], "--string-oom") == 0)
		return exhausted_string_clone(0);
	if (argc == 2 && strcmp(argv[1], "--string-copy-oom") == 0)
		return exhausted_string_clone(1);
	if (argc != 1) {
		fputs("Usage: emberbsd-upb-oom-contract "
		    "[--array-oom|--string-oom|--string-copy-oom]\n", stderr);
		return 2;
	}
	if (exhausted_message_clone() != 0)
		return 1;
	if (exhausted_array_clone() != 0 || exhausted_string_clone(0) != 0)
		return 1;
	return exhausted_string_clone(1);
}
