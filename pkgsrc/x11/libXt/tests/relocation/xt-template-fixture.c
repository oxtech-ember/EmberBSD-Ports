/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
char *probe(const char *);
int main(int argc, char **argv) {
 if (argc != 2) return 2;
 char expected[4096];
 const char *a="/original/sdk/share/%N/%:x:/outside/%%:/original/sdk/share/%D:%N:/original/sdk/share/%N/../evil:/outside/%";
 snprintf(expected,sizeof expected,"%s/share/%%N/%%:x:/outside/%%%%:%s/share/%%D:%%N:/original/sdk/share/%%N/../evil:/outside/%%",argv[1],argv[1]);
 const char *e=expected;
 char *got=probe(a);int ok=got&&!strcmp(got,e);if(!ok) printf("got: %s\n",got?got:"NULL");free(got);puts(ok?"Xt template PASS":"Xt template FAIL");return !ok;
}
