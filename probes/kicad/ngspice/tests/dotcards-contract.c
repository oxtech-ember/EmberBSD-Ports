/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Internal parser regression, not a public API. */
#include <stdbool.h>
#include <ngspice/sharedspice.h>
#include <ngspice/wordlist.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern wordlist *gettoks(char *);
static unsigned diagnostics;

static int
send_text(char *text, int ident, void *context)
{
	(void)ident;
	(void)context;
	if (strstr(text, "missing ')'"))
		++diagnostics;
	return 0;
}

static int
controlled_exit(int status, bool immediate, bool quit, int ident, void *context)
{
	(void)status;
	(void)immediate;
	(void)quit;
	(void)ident;
	(void)context;
	return 0;
}

int
main(void)
{
	const size_t length = 32768;
	char *expression = malloc(length + 4);
	wordlist *words;
	bool good;
	char malformed[] = "v(in,out";
	char quit[] = "quit";

	if (!expression)
		return 2;
	expression[0] = 'i';
	expression[1] = '(';
	memset(expression + 2, 'x', length);
	expression[length + 2] = ')';
	expression[length + 3] = '\0';
	ngSpice_nospiceinit();
	if (ngSpice_Init(send_text, NULL, controlled_exit, NULL, NULL, NULL,
	    NULL) != 0) {
		free(expression);
		return 1;
	}
	words = gettoks(expression);
	good = words && !words->wl_next && words->wl_word &&
	    strlen(words->wl_word) == length + 7 &&
	    memcmp(words->wl_word, expression + 2, length) == 0 &&
	    strcmp(words->wl_word + length, "#branch") == 0;
	wl_free(words);
	free(expression);
	words = gettoks(malformed);
	good = good && words == NULL && diagnostics == 1;
	wl_free(words);
	ngSpice_Command(quit);
	puts(good ? "PASS: complete 32KiB current vector and missing parenthesis rejection" :
	    "FAIL: internal dot-card parser contract");
	return good ? 0 : 1;
}
