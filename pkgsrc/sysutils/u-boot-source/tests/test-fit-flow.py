# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
from common import arguments, compile_and_run
args = arguments('Check FIT handoff control flow')
src = (args.source / 'common/spl/spl_fit.c').read_text()
start=src.index('int spl_load_simple_fit(struct spl_image_info *spl_image,')
end=src.index('\n/* Parse and load full fitImage in SPL */',start)
actual=src[start:end]
header=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef unsigned long ulong;
#define CONFIG_SPL_FPGA 0
#define CONFIG_SPL_OS_BOOT 0
#define CONFIG_FIT_IMAGE_TINY 0
#define IS_ENABLED(x) (x)
#define CONFIG_IS_ENABLED(x) CONFIG_##x
#define FIT_FIRMWARE_PROP "firmware"
#define FIT_KERNEL_PROP "kernel"
#define CONFIG_SYS_BOOTM_LEN 0x20000
#define IH_OS_INVALID 0
#define IH_OS_U_BOOT 1
#define IH_OS_TEE 2
#define IH_OS_LINUX 3
#define EBADSLT 57
#define FDT_ERROR (~0UL)
#define SPL_FIT_FOUND 1
#define debug(...) ((void)0)
struct spl_image_info {
	ulong load_addr, entry_point;
	uint8_t os;
	void *fdt_addr;
	int flags;
};
struct spl_load_info {
	int unused;
};
struct spl_fit_info {
	void *fit;
	int conf_node;
};
static int append_status, loadable_os, calls;
static int original_fdt, new_fdt;
static int
spl_simple_fit_read(struct spl_fit_info *c, struct spl_load_info *i, ulong o,
		    void *f)
{
	(void)i;
	(void)o;
	c->fit = f;
	return 0;
}
static int
spl_load_simple_fit_skip_processing(void)
{
	return 0;
}
static void *
spl_load_simple_fit_fix_load(void *f)
{
	return f;
}
static int
spl_simple_fit_parse(struct spl_fit_info *c)
{
	c->conf_node = 0;
	return 0;
}
static void
spl_fit_load_fpga(struct spl_fit_info *c, struct spl_load_info *i, ulong o)
{
	(void)c;
	(void)i;
	(void)o;
}
static int
spl_fit_get_image_node(struct spl_fit_info *c, const char *p, int i)
{
	(void)c;
	if (!strcmp(p, "firmware"))
		return 1;
	if (!strcmp(p, "loadables") && i == 0)
		return 2;
	return -1;
}
static int
load_simple_fit(struct spl_load_info *i, ulong o, struct spl_fit_info *c, int n,
		struct spl_image_info *img, int limit)
{
	(void)i;
	(void)o;
	(void)c;
	(void)n;
	(void)limit;
	img->load_addr = 0x1000;
	img->entry_point = 0x1000;
	return 0;
}
static int
spl_fit_image_get_os(void *f, int n, uint8_t *os)
{
	(void)f;
	*os = n == 1 ? IH_OS_TEE : loadable_os;
	return 0;
}
static int
os_takes_devicetree(int os)
{
	return os == IH_OS_U_BOOT || os == IH_OS_LINUX;
}
static int
spl_fit_append_fdt(struct spl_image_info *i, struct spl_load_info *l, ulong o,
		   struct spl_fit_info *c)
{
	(void)l;
	(void)o;
	(void)c;
	calls++;
	if (append_status >= 0)
		i->fdt_addr = &new_fdt;
	return append_status;
}
static int
spl_fit_image_is_fpga(void *f, int n)
{
	(void)f;
	(void)n;
	return 0;
}
static void
spl_fit_upload_fpga(struct spl_fit_info *c, int n, struct spl_image_info *i)
{
	(void)c;
	(void)n;
	(void)i;
}
static void
spl_fit_image_record_arm32_optee(void *f, int n, struct spl_image_info *a,
				 struct spl_image_info *b)
{
	(void)f;
	(void)n;
	(void)a;
	(void)b;
}
static int
xpl_get_fdt_update(struct spl_load_info *i)
{
	(void)i;
	return 0;
}
static void
spl_fit_record_loadable(struct spl_fit_info *c, int n, void *f,
			struct spl_image_info *i)
{
	(void)c;
	(void)n;
	(void)f;
	(void)i;
}
static ulong
map_to_sysmem(void *p)
{
	return (ulong)p;
}
static void
upl_set_fit_info(ulong x, int y, ulong z)
{
	(void)x;
	(void)y;
	(void)z;
}
'''
tests=r'''
static void
run_case(int os, int code, int expected, void *expected_fdt)
{
	struct spl_image_info image = {.fdt_addr = &original_fdt};
	struct spl_load_info info = {0};
	loadable_os = os;
	append_status = code;
	calls = 0;
	assert(spl_load_simple_fit(&image, &info, 0, (void *)1) == expected);
	assert(calls == 1);
	assert(image.fdt_addr == expected_fdt);
}
int
main(void)
{
	run_case(IH_OS_U_BOOT, 0, 0, &new_fdt);
	run_case(IH_OS_U_BOOT, 4096, 0, &new_fdt);
	run_case(IH_OS_U_BOOT, -5, 0, &original_fdt);
	run_case(IH_OS_LINUX, -5, -5, &original_fdt);
	puts("four FIT handoff cases passed (actual source, mocked "
	     "collaborators)");
}
'''
compile_and_run(args, header + actual + tests, cflags=('-Wall', '-Wextra', '-Werror'))
