/* SPDX-License-Identifier: BSD-2-Clause
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <plist/plist.h>

static size_t fail_size;

void *
plist_test_malloc(size_t size)
{
	return size == fail_size ? NULL : malloc(size);
}

int
main(int argc, char **argv)
{
	plist_t node = NULL, item;
	char *output = NULL;
	uint32_t length = 0;
	plist_err_t result;

	if (argc != 2)
		return 2;
	if (strcmp(argv[1], "parse") == 0) {
		fail_size = 14;
		result = plist_from_openstep("\"abcdefghijklm\"", 15, &node);
	} else {
		node = plist_new_array();
		if (node == NULL)
			return 3;
		if (strstr(argv[1], "uid") != NULL)
			item = plist_new_uid(1);
		else if (strstr(argv[1], "real") != NULL)
			item = plist_new_real(1.5);
		else
			item = plist_new_uint(1);
		if (item == NULL)
			return 3;
		plist_array_append_item(node, item);
		fail_size = 64;
		if (strncmp(argv[1], "json", 4) == 0)
			result = plist_to_json_with_options(node, &output, &length,
			    PLIST_OPT_COERCE);
		else
			result = plist_to_openstep_with_options(node, &output, &length,
			    PLIST_OPT_COERCE);
	}
	plist_free(node);
	free(output);
	return result == PLIST_ERR_NO_MEM ? 0 : 4;
}
