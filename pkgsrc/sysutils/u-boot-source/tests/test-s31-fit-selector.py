#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
"""Check S31 external FIT layout and real SPL FIT configuration selection."""
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
#include <stdint.h>
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

static int
s31_fit_uses_external_data(const void *fit, size_t fit_size)
{
	static const char *const images[] = { "firmware", "uboot", "fdt" };
	size_t fit_header_size = ((size_t)fdt_totalsize(fit) + 3) & ~(size_t)3;
	size_t data_size;
	int images_node = fdt_path_offset(fit, "/images");
	size_t previous_end = 0;
	unsigned int i;

	if (fit_header_size > fit_size || images_node < 0)
		return 0;
	data_size = fit_size - fit_header_size;
	for (i = 0; i < sizeof(images) / sizeof(images[0]); i++) {
		const fdt32_t *offset_prop, *size_prop;
		int node, len;
		uint32_t offset, size;

		node = fdt_subnode_offset(fit, images_node, images[i]);
		if (node < 0 || fdt_getprop(fit, node, "data", &len) != NULL ||
		    len != -FDT_ERR_NOTFOUND)
			return 0;
		offset_prop = fdt_getprop(fit, node, "data-offset", &len);
		if (!offset_prop || len != sizeof(*offset_prop))
			return 0;
		size_prop = fdt_getprop(fit, node, "data-size", &len);
		if (!size_prop || len != sizeof(*size_prop))
			return 0;
		offset = fdt32_to_cpu(*offset_prop);
		size = fdt32_to_cpu(*size_prop);
		if (offset < previous_end || offset > data_size ||
		    size > data_size - offset)
			return 0;
		previous_end = (size_t)offset + size;
	}
	return 1;
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
	if (!s31_fit_uses_external_data(fit, (size_t)size)) {
		fprintf(stderr, "S31 FIT must store firmware, U-Boot and FDT "
		    "as ordered external data\n");
		return 5;
	}
	expected = fdt_path_offset(fit, "/configurations/conf");
	selected = fit_find_config_node(fit);
	if (expected < 0 || selected != expected)
		return 6;
	printf("S31 external FIT layout valid; SPL selector chose %s\n",
	    fdt_get_name(fit, selected, NULL));
	free(fit);
	return 0;
}
'''
compile_and_run(args, program, include=(args.host_prefix / 'include',),
                libraries=('fdt',), cflags=('-Wall', '-Wextra', '-Werror'),
                run_args=(str(fit),))
