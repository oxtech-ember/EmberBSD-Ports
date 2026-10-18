/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Count real copied-key lifetime on failure. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include "linkhash.h"

static void *copied_key;
static int releases;

static char *
tracked_strdup(const char *key)
{

	copied_key = strdup(key);
	return copied_key;
}

static void
tracked_free(void *pointer)
{

	if (pointer != NULL && pointer == copied_key) {
		releases++;
		copied_key = NULL;
	}
	free(pointer);
}

/* Instrument allocation ownership in the actual production translation unit. */
#define strdup tracked_strdup
#define free tracked_free
#include "json_object.c"
#undef strdup
#undef free

int
main(void)
{
	struct json_object *object, *value;
	struct lh_table *table;
	int rc, old_size;

	object = json_object_new_object();
	value = json_object_new_int(7);
	if (object == NULL || value == NULL)
		return 2;
	table = json_object_get_object(object);
	old_size = table->size;
	/* Exercise the real maximum-capacity failure without a huge allocation. */
	table->size = INT_MAX;
	table->count = INT_MAX;
	rc = json_object_object_add_ex(object, "copied-key", value,
	    JSON_C_OBJECT_ADD_KEY_IS_NEW);
	if (rc != -1 || releases != 1 || copied_key != NULL) {
		fprintf(stderr, "FAIL: copied key remains allocated after insertion failure\n");
		return 1;
	}
	rc = json_object_object_add_ex(object, "constant-key", value,
	    JSON_C_OBJECT_ADD_CONSTANT_KEY | JSON_C_OBJECT_ADD_KEY_IS_NEW);
	if (rc != -1 || releases != 1)
		return 1;
	table->size = old_size;
	table->count = 0;
	if (json_object_get_int(value) != 7)
		return 1;
	json_object_put(value);
	json_object_put(object);
	puts("PASS: failed insertion releases its copied key; constant key and value remain caller-owned");
	return 0;
}
