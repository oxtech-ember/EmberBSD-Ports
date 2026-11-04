/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#ifndef EMBER_EXECPATH_H
#define EMBER_EXECPATH_H
#include <sys/types.h>
#include <sys/stat.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdio.h>

/* Only expand the exact selected token; retain the sibling's invocation name. */
static char *
ember_execpath(const char *arg0, const char *value)
{
	static const char token[] = "@executable_path/";
	char resolved[PATH_MAX], candidate[PATH_MAX], *path, *part, *next, *out;
	struct stat st;
	size_t len;
	int found = 0, length;

	if (strncmp(value, token, sizeof(token) - 1) != 0)
		return strdup(value);
	if (arg0 == NULL || *arg0 == '\0') {
		errno = ENOENT;
		return NULL;
	}
	resolved[0] = '\0';
	if (strchr(arg0, '/') != NULL) {
		if (realpath(arg0, resolved) == NULL)
			return NULL;
	} else {
		path = getenv("PATH");
		if (path == NULL) {
			errno = ENOENT;
			return NULL;
		}
		if ((path = strdup(path)) == NULL)
			return NULL;
		part = path;
		for (;;) {
			next = strchr(part, ':');
			if (next != NULL)
				*next++ = '\0';
			length = snprintf(candidate, sizeof(candidate), "%s/%s",
			    *part ? part : ".", arg0);
			if (length >= 0 && length < (int)sizeof(candidate) &&
			    stat(candidate, &st) == 0 && S_ISREG(st.st_mode) &&
			    access(candidate, X_OK) == 0 &&
			    realpath(candidate, resolved) != NULL) {
				found = 1;
				break;
			}
			if (next == NULL)
				break;
			part = next;
		}
		free(path);
		if (!found) {
			errno = ENOENT;
			return NULL;
		}
	}
	part = strrchr(resolved, '/');
	if (part == NULL) {
		errno = EINVAL;
		return NULL;
	}
	*part = '\0';
	len = strlen(resolved) + strlen(value + sizeof(token) - 1) + 2;
	out = malloc(len);
	if (out != NULL)
		snprintf(out, len, "%s/%s", resolved, value + sizeof(token) - 1);
	return out;
}

static char *
ember_shell_quote(const char *value)
{
	const char *p;
	char *out, *q;
	size_t n = 3;

	for (p = value; *p; p++)
		n += *p == '\'' ? 4 : 1;
	if ((out = malloc(n)) == NULL)
		return NULL;
	q = out;
	*q++ = '\'';
	for (p = value; *p; p++) {
		if (*p == '\'') {
			memcpy(q, "'\\''", 4);
			q += 4;
		} else
			*q++ = *p;
	}
	*q++ = '\'';
	*q = '\0';
	return out;
}
#endif
