/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Actual common-string memory checks. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "stringop.h"

#define CHECK(value) do { if (!(value)) { \
	fprintf(stderr, "FAIL: %s\n", #value); return 1; } } while (0)

int
main(void)
{
	char spaced[] = "\t a b \n", empty[] = " \t\n";
	char high[] = " \xff X \t", quoted[] = "\"a b\"";
	char escaped[] = "a\\nb\\t";
	char *words[] = { "a", "b c" }, *joined, **arguments;
	int count;

	strip_whitespace(spaced);
	CHECK(strcmp(spaced, "a b") == 0);
	strip_whitespace(empty);
	CHECK(empty[0] == '\0');
	strip_whitespace(high);
	CHECK(strcmp(high, "\xff X") == 0);
	strip_quotes(quoted);
	CHECK(strcmp(quoted, "a b") == 0);
	arguments = split_args("[title=\"two three\"] one \"four five\"", &count);
	CHECK(arguments != NULL && count == 3);
	CHECK(strcmp(arguments[0], "[title=\"two three\"]") == 0);
	CHECK(strcmp(arguments[1], "one") == 0);
	CHECK(strcmp(arguments[2], "\"four five\"") == 0);
	CHECK(arguments[3] == NULL);
	free_argv(count, arguments);
	arguments = split_args(NULL, &count);
	CHECK(arguments != NULL && count == 0 && arguments[0] == NULL);
	free_argv(count, arguments);
	joined = join_args(words, 2);
	CHECK(joined != NULL && strcmp(joined, "a b c") == 0);
	free(joined);
	CHECK(unescape_string(escaped) == 4 && strcmp(escaped, "a\nb\t") == 0);
	CHECK(lenient_strcmp(NULL, NULL) == 0);
	CHECK(lenient_strcmp("a", "b") < 0);
	puts("PASS: 14 actual string contracts, including high bytes and quoted arguments");
	return 0;
}
