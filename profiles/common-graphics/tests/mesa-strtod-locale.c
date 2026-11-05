/* SPDX-License-Identifier: MIT */
/* Exercise the actual Mesa numeric conversion under a comma locale. */
#include <locale.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "util/strtod.h"

/* Standalone harness supplies the same cleanup contract as Mesa util. */
int util_atexit(void (*fn)(void)) { return atexit(fn); }

static int check(const char *locale)
{
   char *end;
   float f = _mesa_strtof("0.333tail", &end);
   if (fabsf(f - 0.333f) > 0.000001f || strcmp(end, "tail")) {
      fprintf(stderr, "%s: strtof value %.9g remainder %s\n", locale, f, end);
      return 1;
   }
   double d = _mesa_strtod("-1.25e+2tail", &end);
   if (d != -125.0 || strcmp(end, "tail")) {
      fprintf(stderr, "%s: strtod value %.17g remainder %s\n", locale, d, end);
      return 1;
   }
   return 0;
}

int main(int argc, char **argv)
{
   if (argc != 2 || !setlocale(LC_NUMERIC, argv[1])) {
      fprintf(stderr, "usage: mesa-strtod-locale INSTALLED_COMMA_LOCALE\n");
      return 2;
   }
   if (strcmp(localeconv()->decimal_point, ",")) {
      fprintf(stderr, "%s is not a comma decimal locale\n", argv[1]);
      return 2;
   }
   if (check(argv[1])) return 1;
   if (!setlocale(LC_NUMERIC, "C") || check("C")) return 1;
   if (!setlocale(LC_NUMERIC, argv[1]) || check(argv[1])) return 1;
   puts("PASS Mesa numeric conversion is locale independent");
   return 0;
}
