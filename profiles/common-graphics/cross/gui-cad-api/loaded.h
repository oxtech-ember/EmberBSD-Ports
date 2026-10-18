/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD; AI-assisted installed-library consumer checks.
 */
#ifndef EMBER_GUI_CAD_LOADED_H
#define EMBER_GUI_CAD_LOADED_H

#include <sys/types.h>
#include <link_elf.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int
loaded(struct dl_phdr_info *info, size_t size, void *argument)
{
	char path[PATH_MAX];
	const char *executable = (const char *)argument;

	(void)size;
	if (info->dlpi_name == NULL || executable == NULL)
		return 1;
	if (info->dlpi_name[0] == '\0' ||
	    strcmp(info->dlpi_name, executable) == 0)
		return 0;
	if (realpath(info->dlpi_name, path) == NULL) {
		perror(info->dlpi_name);
		return 1;
	}
	printf("LOADED: %s\n", path);
	return 0;
}

static void
check_loaded(const char *executable)
{

	if (dl_iterate_phdr(loaded, (void *)executable) != 0)
		exit(1);
}

#endif
