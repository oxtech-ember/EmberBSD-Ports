# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check FIT full-read and alignment handling')
root = args.source
def function(file, marker):
    s=(root/file).read_text(); start=s.index(marker); brace=s.index('{', start); depth=1; end=brace+1
    while depth:
        if s[end]=='{': depth+=1
        elif s[end]=='}': depth-=1
        end+=1
    return s[start:end]+'\n'
preamble=r'''#include <errno.h>
#include <libfdt.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned long ulong;
typedef uint32_t u32;
#define FIT_FULL_CHECK 1
#define FIT_SIGNATURE 0
#define CONTROL_DTB_AS_FIT 0
#define CONFIG_IS_ENABLED(x) x
#define FIT_IMAGES_PATH "/images"
#define FIT_DESC_PROP "description"
#define FIT_TIMESTAMP_PROP "timestamp"
#define IMAGE_ENABLE_TIMESTAMP 0
#define IMAGE_SIZE_INVAL (~0UL)
#define FDT_MAX_DEPTH 128
#define log_debug(...) ((void)0)
#define debug(...) ((void)0)
#define ALIGN(x, a) (((x) + (a) - 1) & ~((a) - 1))
struct spl_load_info {
	ulong (*read)(struct spl_load_info *, ulong, ulong, void *);
};
struct spl_fit_info {
	ulong ext_data_offset;
	void *fit;
};
static const void *
gd_fdt_blob(void)
{
	return NULL;
}
static int oversized_alignment;
static ulong
board_spl_fit_size_align(ulong n)
{
	return oversized_alignment ? ULONG_MAX - 1 : n;
}
static int
get_aligned_image_size(struct spl_load_info *i, ulong n, u32 off, ulong *out)
{
	(void)i;
	(void)off;
	*out = ALIGN(n, 4096);
	return 0;
}
static void *last_buffer;
static void *
board_spl_fit_buffer_addr(ulong n, ulong a, int x)
{
	(void)a;
	(void)x;
	return last_buffer = malloc(n);
}
'''
main=r'''static void *input;
static int short_read;
static size_t input_size;
static ulong
reader(struct spl_load_info *i, ulong off, ulong count, void *dst)
{
	(void)i;
	(void)off;
	if (count <= input_size)
		abort();
	if (short_read == 2)
		return ~0UL;
	size_t n = input_size - (short_read ? 1 : 0);
	memcpy(dst, input, n);
	return n;
}
int
main(void)
{
	struct spl_load_info info = {reader};
	struct spl_fit_info ctx = {0};
	int ret;
	input = calloc(1, 2048);
	if (!input)
		return 1;
	if (fdt_create_empty_tree(input, 2048))
		return 2;
	if (fdt_setprop_string(input, 0, "description", "host fixture"))
		return 3;
	if (fdt_add_subnode(input, 0, "images") < 0 || fdt_pack(input))
		return 3;
	input_size = fdt_totalsize(input);
	ret = spl_simple_fit_read(&ctx, &info, 0, input);
	if (ret || !ctx.fit)
		return 4;
	free(ctx.fit);
	ctx.fit = NULL;
	short_read = 1;
	ret = spl_simple_fit_read(&ctx, &info, 0, input);
	if (ret != -EIO || ctx.fit)
		return 5;
	free(last_buffer);
	short_read = 2;
	ret = spl_simple_fit_read(&ctx, &info, 0, input);
	if (ret != -EIO || ctx.fit)
		return 6;
	free(last_buffer);
	oversized_alignment = 1;
	ret = spl_simple_fit_read(&ctx, &info, 0, input);
	if (ret != -EOVERFLOW || ctx.fit)
		return 7;
	free(input);
	puts("real FIT check: unpadded image accepted; incomplete/over-limit "
	     "reads and alignment overflow rejected");
	return 0;
}
'''
s=preamble
for name in ('static int fdt_check_no_at(', 'static int fit_check_images_node(', 'int fit_check_format('): s+=function('boot/image-fit.c',name)
s+=function('common/spl/spl_fit.c','static int spl_simple_fit_read(')+main
compile_and_run(args, s, include=(args.host_prefix / 'include',), libraries=('fdt',))
