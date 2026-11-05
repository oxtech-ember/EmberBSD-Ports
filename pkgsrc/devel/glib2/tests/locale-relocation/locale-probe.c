/* Synthetic GLib locale and loaded-image regression. */
#define _GNU_SOURCE 1
#include <glib.h>
#include <dlfcn.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern const gchar *glib_gettext (const gchar *str);

int main(int argc, char **argv) {
  Dl_info info;
  char *actual, *expected;
  const char *value;
  if (argc != 3 || !setlocale(LC_ALL, "")) return 2;
  if (!dladdr((const void *)glib_gettext, &info) || !info.dli_fname) return 3;
  actual = realpath(info.dli_fname, NULL);
  expected = realpath(argv[1], NULL);
  if (!actual || !expected || strcmp(actual, expected)) return 4;
  value = glib_gettext("EMBERBSD synthetic relocated locale probe");
  printf("loaded=%s\ntranslation=%s\n", actual, value);
  free(actual);
  free(expected);
  return strcmp(value, argv[2]) != 0;
}
