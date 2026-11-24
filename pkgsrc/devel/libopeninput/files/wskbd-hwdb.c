/*	$NetBSD$	*/
/* SPDX-License-Identifier: MIT */

/*
 * Keyboard scan code mappings from systemd hwdb files.  See hwdb(7) of
 * systemd for the file format.
 *
 * A record is one or more match lines and then the property lines, each
 * with a leading space.  An empty line ends the record; a line that starts
 * with '#' is a comment.  A match line is a fnmatch(3) pattern.  On Linux,
 * udev matches PC keyboards with "evdev:atkbd:" and with
 * "evdev:name:AT Translated Set 2 keyboard:", each followed by the DMI
 * modalias.  The atkbd scan code of an escaped (e0) code has bit 7 set, as
 * the wscons key of the XT translation.
 */

#include <ctype.h>
#include <dirent.h>
#include <fnmatch.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "wskbd-hwdb.h"
#include "wskbd-keynames.h"

#define HWDB_LINE	1024
#define HWDB_KEY	"KEYBOARD_KEY_"

static const char *const hwdb_devices[] = {
	"evdev:atkbd:",
	"evdev:name:AT Translated Set 2 keyboard:",
};

#define NDEVICES	(sizeof(hwdb_devices) / sizeof(hwdb_devices[0]))

int
wskbd_hwdb_modalias(const struct wskbd_hwdb_dmi *dmi, char *buf, size_t size)
{
	const struct {
		const char *prefix;
		const char *value;
	} fields[] = {
		{ "bvn", dmi->bvn }, { "bvr", dmi->bvr }, { "bd", dmi->bd },
		{ "svn", dmi->svn }, { "pn", dmi->pn }, { "pvr", dmi->pvr },
		{ "rvn", dmi->rvn }, { "rn", dmi->rn }, { "rvr", dmi->rvr },
		{ "cvn", dmi->cvn }, { "cvr", dmi->cvr },
	};
	size_t i, len;
	const char *s;

	if (size < sizeof("dmi:"))
		return -1;
	strcpy(buf, "dmi:");
	len = strlen(buf);
	for (i = 0; i < sizeof(fields) / sizeof(fields[0]); i++) {
		if (len + strlen(fields[i].prefix) + 1 >= size)
			return -1;
		strcpy(buf + len, fields[i].prefix);
		len += strlen(fields[i].prefix);
		s = fields[i].value != NULL ? fields[i].value : "";
		for (; *s != '\0'; s++) {
			if (*s <= ' ' || *s >= 127 || *s == ':')
				continue;
			if (len + 2 >= size)
				return -1;
			buf[len++] = *s;
		}
		buf[len++] = ':';
		buf[len] = '\0';
	}
	return 0;
}

int
wskbd_hwdb_key(const char *name)
{
	char full[64];
	size_t i;

	/* The names are the evdev names in lower case, without "key_". */
	if (strncmp(name, "btn_", 4) == 0)
		snprintf(full, sizeof(full), "%s", name);
	else
		snprintf(full, sizeof(full), "key_%s", name);
	for (i = 0; i < sizeof(wskbd_key_names) / sizeof(wskbd_key_names[0]);
	    i++) {
		if (strcmp(wskbd_key_names[i].name, full) == 0)
			return wskbd_key_names[i].code;
	}
	return -1;
}

/* Remove trailing white space of S. */
static void
hwdb_trim(char *s)
{
	size_t len = strlen(s);

	while (len > 0 && isspace((unsigned char)s[len - 1]))
		s[--len] = '\0';
}

/* Apply the property P ("KEYBOARD_KEY_91=config") to MAP. */
static int
hwdb_property(char *p, uint32_t *map, size_t size)
{
	char *end, *comment;
	unsigned long scan;
	int key;

	if ((comment = strchr(p, '#')) != NULL)
		*comment = '\0';
	hwdb_trim(p);
	if (strncmp(p, HWDB_KEY, strlen(HWDB_KEY)) != 0)
		return 0;
	p += strlen(HWDB_KEY);
	if (!isxdigit((unsigned char)*p))
		return 0;
	scan = strtoul(p, &end, 16);
	if (*end != '=' || scan >= size)
		return 0;
	p = end + 1;
	/* '!': the key sends no release; wscons sends each release. */
	if (*p == '!')
		p++;
	if ((key = wskbd_hwdb_key(p)) < 0)
		return 0;
	map[scan] = (uint32_t)key;
	return 1;
}

static size_t
hwdb_file(FILE *fp, char *const *matches, uint32_t *map, size_t size)
{
	char line[HWDB_LINE];
	size_t i, applied = 0;
	int c, data = 0, record = 0, matched = 0;

	while (fgets(line, sizeof(line), fp) != NULL) {
		if (strchr(line, '\n') == NULL && !feof(fp)) {
			/* A line that is too long: ignore all of it. */
			while ((c = getc(fp)) != EOF && c != '\n')
				continue;
			continue;
		}
		hwdb_trim(line);
		if (line[0] == '#')
			continue;
		if (line[0] == '\0') {
			record = 0;
			continue;
		}
		if (line[0] != ' ' && line[0] != '\t') {
			/* A match line after the properties starts a record. */
			if (!record || data)
				matched = data = 0;
			record = 1;
			for (i = 0; i < NDEVICES && !matched; i++)
				matched = fnmatch(line, matches[i], 0) == 0;
			continue;
		}
		if (!record)
			continue;
		data = 1;
		if (matched)
			applied += hwdb_property(line + strspn(line, " \t"), map,
			    size);
	}
	return applied;
}

static int
hwdb_compare(const void *a, const void *b)
{
	return strcmp(*(char *const *)a, *(char *const *)b);
}

size_t
wskbd_hwdb_apply(const char *dir, const char *modalias, uint32_t *map,
    size_t size)
{
	char *matches[NDEVICES], **names = NULL, **grown, path[1024];
	struct dirent *entry;
	size_t i, len, count = 0, room = 0, applied = 0;
	int complete = 1;
	DIR *d;
	FILE *fp;

	for (i = 0; i < NDEVICES; i++)
		matches[i] = NULL;
	for (i = 0; i < NDEVICES; i++) {
		len = strlen(hwdb_devices[i]) + strlen(modalias) + 1;
		if ((matches[i] = malloc(len)) == NULL)
			goto out;
		snprintf(matches[i], len, "%s%s", hwdb_devices[i], modalias);
	}
	if ((d = opendir(dir)) == NULL)
		goto out;
	while ((entry = readdir(d)) != NULL) {
		len = strlen(entry->d_name);
		if (entry->d_name[0] == '.' || len < 6 ||
		    strcmp(entry->d_name + len - 5, ".hwdb") != 0)
			continue;
		if (count == room) {
			room = room == 0 ? 16 : room * 2;
			if ((grown = realloc(names, room * sizeof(*names))) ==
			    NULL) {
				complete = 0;
				break;
			}
			names = grown;
		}
		if ((names[count] = strdup(entry->d_name)) == NULL) {
			complete = 0;
			break;
		}
		count++;
	}
	closedir(d);
	/* Without all names, the order of the files is not known. */
	if (complete && count > 0) {
		qsort(names, count, sizeof(names[0]), hwdb_compare);
		for (i = 0; i < count; i++) {
			snprintf(path, sizeof(path), "%s/%s", dir, names[i]);
			if ((fp = fopen(path, "r")) != NULL) {
				applied += hwdb_file(fp, matches, map, size);
				fclose(fp);
			}
		}
	}
	for (i = 0; i < count; i++)
		free(names[i]);
	free(names);
out:
	for (i = 0; i < NDEVICES; i++)
		free(matches[i]);
	return applied;
}
