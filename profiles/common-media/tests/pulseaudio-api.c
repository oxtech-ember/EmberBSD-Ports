/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted). Locale conversion and caller-buffer contracts.
 */
#include <assert.h>
#include <locale.h>
#include <stdio.h>
#include <string.h>
#include <pulse/utf8.h>
#include <pulse/util.h>
#include <pulse/xmalloc.h>

static void
convert(const char *value)
{
	char *utf8 = pa_locale_to_utf8(value);
	assert(utf8 != NULL && strcmp(utf8, value) == 0);
	char *local = pa_utf8_to_locale(utf8);
	assert(local != NULL && strcmp(local, value) == 0);
	pa_xfree(local);
	pa_xfree(utf8);
}

int
main(int argc, char **argv)
{
	assert(argc == 2);
	if (strcmp(argv[1], "locale") == 0) {
		assert(setlocale(LC_ALL, "C") != NULL);
		convert("PulseAudio ASCII");
		assert(pa_locale_to_utf8("\xff") == NULL);
		assert(setlocale(LC_ALL, "en_US.UTF-8") != NULL);
		convert("PulseAudio \xcf\x80 \xc3\xa9");
		assert(pa_locale_to_utf8("\xff") == NULL);
		puts("PASS: C/UTF-8 locale round trips and invalid input refusal");
	} else {
		assert(strcmp(argv[1], "name") == 0);
		const char *name = strrchr(argv[0], '/');
		name = name != NULL ? name + 1 : argv[0];
		char buffer[1024], tiny[3];
		memset(buffer, 'X', sizeof(buffer));
		assert(pa_get_binary_name(buffer, sizeof(buffer)) == buffer);
		assert(strcmp(buffer, name) == 0);
		memset(tiny, 'X', sizeof(tiny));
		assert(pa_get_binary_name(tiny, sizeof(tiny)) == tiny);
		assert(tiny[2] == '\0' && strncmp(tiny, name, 2) == 0);
		puts("PASS: binary-name return pointer, basename and bounded caller buffer");
	}
	return 0;
}
