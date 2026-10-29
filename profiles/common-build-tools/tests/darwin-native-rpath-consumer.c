/* SPDX-License-Identifier: BSD-2-Clause */
/* Exercise both an @rpath dependency and an absolute install name. */
#include <glib.h>
#include <libxml/parser.h>

int
main(void)
{
	GString *s = g_string_new("hello");
	int ok = s->len == 5 && xmlParserVersion != 0;

	g_string_free(s, 1);
	return !ok;
}
