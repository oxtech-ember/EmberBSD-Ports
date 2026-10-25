/* SPDX-License-Identifier: BSD-2-Clause */
/* Unit fixture. It does not inspect the host filesystem or active cache. */
#include <sys/stat.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef TEST_DYLD_CACHE
#error Define TEST_DYLD_CACHE as 0 or 1.
#endif
#if TEST_DYLD_CACHE
#define PKG_INSTALL_DYLD_SHARED_CACHE 1
#endif

static char *Destdir;
static int Force;
static int host_kind, target_kind, cache_hit, cache_calls, warnings;
static const char *required_path;
static char rooted_path[512];

struct pkg_task {
	const char *pkgname;
	struct { const char *meta_build_info; } meta_data;
};

static bool
cache_contains(const char *path)
{
	++cache_calls;
	if (strcmp(path, required_path) != 0)
		abort();
	return cache_hit != 0;
}

static bool (*cache_query)(const char *);
#define _dyld_shared_cache_contains_path cache_query

static int
fixture_stat(const char *path, struct stat *sb)
{
	int kind = strcmp(path, required_path) == 0 ? host_kind :
	    strcmp(path, rooted_path) == 0 ? target_kind : 0;
	if (kind == 0)
		return -1;
	sb->st_mode = kind == 1 ? S_IFREG : S_IFDIR;
	return 0;
}
#define stat(path, sb) fixture_stat(path, sb)

static void
fixture_warnx(const char *format, ...)
{
	(void)format;
	++warnings;
}
#define warnx fixture_warnx

static char *
dup_value(const char *start, const char *end)
{
	char *copy;
	size_t len;
	start = strchr(start, '=') + 1;
	len = (size_t)(end - start);
	copy = malloc(len + 1);
	if (copy == NULL)
		abort();
	memcpy(copy, start, len);
	copy[len] = '\0';
	return copy;
}

static char *
xasprintf(const char *format, ...)
{
	va_list ap;
	char *text;
	int len;
	va_start(ap, format);
	len = vsnprintf(NULL, 0, format, ap);
	va_end(ap);
	if (len < 0 || (text = malloc((size_t)len + 1)) == NULL)
		abort();
	va_start(ap, format);
	vsnprintf(text, (size_t)len + 1, format, ap);
	va_end(ap);
	return text;
}

/* Generated from the actual patched perform.c, without reimplementation. */
#include "pkg-install-check-requires.inc"

int
main(void)
{
	static const struct {
		const char *name, *destdir, *path;
		int host, target, api, hit, expected, queries;
	} cases[] = {
		{ "cache hit", NULL, "/usr/lib/test.dylib", 0, 0, 1, 1,
		    TEST_DYLD_CACHE ? 0 : 1, TEST_DYLD_CACHE },
		{ "cache miss", NULL, "/usr/lib/missing.dylib", 0, 0, 1, 0,
		    1, TEST_DYLD_CACHE },
		{ "old runtime", NULL, "/usr/lib/test.dylib", 0, 0, 0, 1, 1, 0 },
		{ "alternate root", "/target", "/usr/lib/test.dylib", 0, 0, 1, 1,
		    1, 0 },
		{ "target file", "/target", "/usr/lib/test.dylib", 0, 1, 1, 0,
		    0, 0 },
		{ "host file", NULL, "/usr/lib/test.dylib", 1, 0, 1, 0, 0, 0 },
		{ "legacy host file with root", "/target", "/usr/lib/test.dylib",
		    1, 0, 1, 0, 0, 0 },
		{ "relative path", NULL, "test.dylib", 0, 0, 1, 1, 1, 0 },
		{ "directory", NULL, "/usr/lib/test.dylib", 2, 0, 1, 0,
		    1, TEST_DYLD_CACHE },
		{ "target directory", "/target", "/usr/lib/test.dylib", 0, 2, 1, 1,
		    1, 0 },
		{ "current root", "/", "/usr/lib/test.dylib", 0, 0, 1, 1,
		    TEST_DYLD_CACHE ? 0 : 1, TEST_DYLD_CACHE }
	};
	size_t i;
	for (i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
		struct pkg_task pkg = { "fixture", { NULL } };
		char data[512];
		int actual;
		Destdir = (char *)cases[i].destdir;
		required_path = cases[i].path;
		host_kind = cases[i].host;
		target_kind = cases[i].target;
		cache_hit = cases[i].hit;
		cache_query = cases[i].api ? cache_contains : NULL;
		Force = cache_calls = warnings = 0;
		snprintf(rooted_path, sizeof(rooted_path), "%s/%s",
		    Destdir != NULL ? Destdir : "", required_path);
		snprintf(data, sizeof(data), "REQUIRES=%s\n", required_path);
		pkg.meta_data.meta_build_info = data;
		actual = check_requires(&pkg);
		if (actual != cases[i].expected || cache_calls != cases[i].queries ||
		    warnings != cases[i].expected) {
			fprintf(stderr, "%s: result %d, queries %d, warnings %d\n",
			    cases[i].name, actual, cache_calls, warnings);
			return 1;
		}
	}
	printf("%zu required-library cases passed (cache feature %d)\n", i,
	    TEST_DYLD_CACHE);
	return 0;
}
