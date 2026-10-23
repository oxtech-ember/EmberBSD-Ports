/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
/* Origin: EmberBSD (AI-assisted). */
#include <locale.h>
#include <libintl.h>
#include <stdio.h>
#include <string.h>

int
main(void)
{
	char *(*locale_fn)(int, const char *) = &setlocale;
	locale_t (*new_fn)(int, const char *, locale_t) = &newlocale;
	const char *name;
	locale_t locale;

	name = locale_fn(LC_ALL, "C");
	locale = new_fn(LC_ALL_MASK, "C", (locale_t)0);
	if (locale == (locale_t)0)
		return 1;
	freelocale(locale);
	if (name == NULL || strcmp(name, "C") != 0)
		return 1;
	puts("locale=C; newlocale=C; address-and-call=OK");
	return 0;
}
