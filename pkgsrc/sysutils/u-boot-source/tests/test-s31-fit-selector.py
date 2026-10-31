#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Run the real SPL FIT configuration selector against a prepared FIT."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
from common import arguments, compile_and_run


def options(parser):
    parser.add_argument('--fit', type=Path, required=True,
                        help='FIT generated from the S31 firmware template')


args = arguments(__doc__, options)
fit = args.fit.resolve(strict=True)
source_file = args.source / 'boot/common_fit.c'
text = source_file.read_text()
start = text.index('int fit_find_config_node(const void *fdt)')
brace = text.index('{', start)
level = 1
end = brace + 1
while level:
    if text[end] == '{':
        level += 1
    elif text[end] == '}':
        level -= 1
    end += 1
selector = text[start:end]
program = r'''#include <errno.h>
#include <libfdt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FIT_CONFS_PATH "/configurations"
#define FIT_DEFAULT_PROP "default"
#define FIT_DESC_PROP "description"
#define CONFIG_SPL_LIBCOMMON_SUPPORT 1
#define debug(...) fprintf(stderr, __VA_ARGS__)

static int
board_fit_config_name_match(const char *name)
{
	(void)name;
	return -EINVAL;
}
'''
program += selector
program += r'''
int
main(int argc, char **argv)
{
	FILE *file;
	void *fit;
	long size;
	int selected, expected;

	if (argc != 2 || !(file = fopen(argv[1], "rb")))
		return 1;
	if (fseek(file, 0, SEEK_END) || (size = ftell(file)) < 0 ||
	    fseek(file, 0, SEEK_SET))
		return 2;
	fit = malloc((size_t)size);
	if (!fit || fread(fit, 1, (size_t)size, file) != (size_t)size)
		return 3;
	fclose(file);
	if (fdt_check_full(fit, (size_t)size))
		return 4;
	expected = fdt_path_offset(fit, "/configurations/conf");
	selected = fit_find_config_node(fit);
	if (expected < 0 || selected != expected)
		return 5;
	printf("actual SPL selector chose %s\n", fdt_get_name(fit, selected, NULL));
	free(fit);
	return 0;
}
'''
compile_and_run(args, program, include=(args.host_prefix / 'include',),
                libraries=('fdt',), cflags=('-Wall', '-Wextra', '-Werror'),
                run_args=(str(fit),))
