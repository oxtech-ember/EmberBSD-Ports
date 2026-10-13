/* SPDX-License-Identifier: BSD-2-Clause */
#include <assert.h>
#include "uthash.h"

struct item {
	int key;
	UT_hash_handle hh;
	UT_hash_handle selected_hh;
};

static int
select_even(void *value)
{
	const struct item *item = (const struct item *)value;

	return (item->key % 2) == 0;
}

static int
select_none(void *value)
{
	(void)value;
	return 0;
}

#define SELECT_ODD(value) ((((struct item *)(value))->key % 2) != 0)

int
main(void)
{
	struct item items[8];
	struct item *source = NULL, *selected = NULL, *found;
	int key;

	/* Neither head names an object. The offset must not evaluate either one. */
	HASH_SELECT(selected_hh, selected, hh, source, select_even);
	assert(selected == NULL);
	for (key = 0; key < 8; key++) {
		items[key].key = key;
		HASH_ADD_INT(source, key, &items[key]);
	}
	HASH_SELECT(selected_hh, selected, hh, source, select_none);
	assert(selected == NULL);
	HASH_SELECT(selected_hh, selected, hh, source, select_even);
	assert(HASH_CNT(selected_hh, selected) == 4);
	for (key = 0; key < 8; key++) {
		HASH_FIND(selected_hh, selected, &key, sizeof(key), found);
		assert((found != NULL) == ((key % 2) == 0));
	}
	HASH_CLEAR(selected_hh, selected);
	HASH_SELECT(selected_hh, selected, hh, source, SELECT_ODD);
	assert(HASH_CNT(selected_hh, selected) == 4);
	for (key = 0; key < 8; key++) {
		HASH_FIND(selected_hh, selected, &key, sizeof(key), found);
		assert((found != NULL) == ((key % 2) != 0));
	}
	HASH_CLEAR(selected_hh, selected);
	HASH_CLEAR(hh, source);
	return 0;
}
