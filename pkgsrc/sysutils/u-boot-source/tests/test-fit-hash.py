# SPDX-License-Identifier: BSD-2-Clause
# Developed with AI assistance.
import sys
sys.dont_write_bytecode = True
import re
from common import arguments, compile_and_run
args = arguments('Check FIT image hash handling')
s = (args.source / 'boot/image-fit.c').read_text()
def get(name):
 m=re.search(r'(?m)^(?:static )?int\s+'+name+r'\s*\([^;{}]*\)\s*\{',s);assert m,name
 i=m.end()-1;d=1;j=i+1
 while d:
  if s[j]=='{':d+=1
  if s[j]=='}':d-=1
  j+=1
 return s[m.start():j]+'\n'
p=r'''#include <libfdt.h>
#include <openssl/evp.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static char output[4096];
static size_t output_len;
static int test_printf(const char *fmt, ...)
{
    va_list ap;
    int n;
    va_start(ap, fmt);
    n = vsnprintf(output + output_len, sizeof(output) - output_len, fmt, ap);
    va_end(ap);
    if (n < 0 || (size_t)n >= sizeof(output) - output_len)
        abort();
    output_len += n;
    return n;
}
static int test_puts(const char *s) { return test_printf("%s", s); }
#define printf test_printf
#define puts test_puts
#define FIT_ALGO_PROP "algo"
#define FIT_VALUE_PROP "value"
#define FIT_IGNORE_PROP "uboot-ignore"
#define FIT_HASH_NODENAME "hash"
#define FIT_SIG_NODENAME "signature"
#define FIT_MAX_HASH_LEN 64
#define ALLOC_CACHE_ALIGN_BUFFER(type, name, len) type name[len]
#define CONFIG_IS_ENABLED(x) 1
#define FIT_IMAGE_ENABLE_VERIFY 0
#define tools_build() 0
#define fit_get_name(f, n, l) fdt_get_name(f, n, l)
#define fit_get_debug(...) ((void)0)
#define gd_fdt_blob() NULL
#define fit_image_verify_required_sigs_quiet(...) 0
#define fit_image_check_sig_quiet(...) 0
static int
calculate_hash(const void *data, int len, const char *name, uint8_t *out,
	       int *outlen)
{
	unsigned int n;
	if (strcmp(name, "sha256"))
		return -1;
	if (!EVP_Digest(data, len, out, &n, EVP_sha256(), NULL))
		return -1;
	*outlen = n;
	return 0;
}
'''
for n in ('fit_image_hash_get_algo','fit_image_hash_get_value','fit_image_hash_get_ignore','fit_image_check_hash','fit_image_verify_with_data_quiet','fit_image_verify_with_data'):p+=get(n)
p+=r'''
#undef printf
#undef puts
static int
add_image(void *tree, const char *name, const char *content)
{
	int images, image, hash;
	unsigned int n;
	unsigned char digest[32];
	images = fdt_path_offset(tree, "/images");
	if (images < 0)
		return -1;
	image = fdt_add_subnode(tree, images, name);
	if (image < 0)
		return -1;
	if (fdt_setprop(tree, image, "data", content, strlen(content)))
		return -1;
	hash = fdt_add_subnode(tree, image, "hash-1");
	if (hash < 0)
		return -1;
	if (fdt_setprop_string(tree, hash, "algo", "sha256"))
		return -1;
	if (!EVP_Digest(content, strlen(content), digest, &n, EVP_sha256(),
			NULL))
		return -1;
	return fdt_setprop(tree, hash, "value", digest, n);
}
int
main(void)
{
	long n;
	void *orig, *copy;
	int node, hash, len, ret, ignore;
	const void *data;
	unsigned char bad[32];

	ignore = 0;
	orig = malloc(8192);
	if (!orig || fdt_create_empty_tree(orig, 8192))
		return 2;
	if (fdt_add_subnode(orig, 0, "images") < 0 ||
	    add_image(orig, "kernel", "kernel fixture") ||
	    add_image(orig, "fdt", "dtb fixture") || fdt_pack(orig))
		return 3;
	n = fdt_totalsize(orig);
	node = fdt_path_offset(orig, "/images/kernel");
	data = fdt_getprop(orig, node, "data", &len);
	if (!data ||
	    fit_image_verify_with_data(orig, node, NULL, data, len) != 1 ||
	    !strstr(output, "sha256+ "))
		return 5;
	output_len = 0;
	output[0] = 0;
	if (fit_image_verify_with_data_quiet(orig, node, NULL, data, len, true, NULL) != 1 ||
	    output_len != 0)
		return 17;
	node = fdt_path_offset(orig, "/images/fdt");
	data = fdt_getprop(orig, node, "data", &len);
	if (!data ||
	    fit_image_verify_with_data(orig, node, NULL, data, len) != 1)
		return 6;
	copy = malloc(n + 4096);
	if (fdt_open_into(orig, copy, n + 4096))
		return 7;
	node = fdt_path_offset(copy, "/images/kernel");
	hash = fdt_subnode_offset(copy, node, "hash-1");
	if (fdt_del_node(copy, hash))
		return 8;
	node = fdt_path_offset(copy, "/images/kernel");
	data = fdt_getprop(copy, node, "data", &len);
	if (fit_image_verify_with_data(copy, node, NULL, data, len) != 0)
		return 9;
	if (fdt_open_into(orig, copy, n + 4096))
		return 10;
	node = fdt_path_offset(copy, "/images/kernel");
	hash = fdt_subnode_offset(copy, node, "hash-1");
	const void *v = fdt_getprop(copy, hash, "value", &len);
	if (!v || len != 32)
		return 11;
	memcpy(bad, v, 32);
	bad[0] ^= 1;
	if (fdt_setprop(copy, hash, "value", bad, 32))
		return 12;
	node = fdt_path_offset(copy, "/images/kernel");
	data = fdt_getprop(copy, node, "data", &len);
	if (fit_image_verify_with_data(copy, node, NULL, data, len) != 0)
		return 13;
	output_len = 0;
	output[0] = 0;
	if (fit_image_verify_with_data_quiet(copy, node, NULL, data, len, true, NULL) != 0 ||
	    output_len == 0)
		return 18;
	hash = fdt_subnode_offset(copy, node, "hash-1");
	if (fdt_setprop_u32(copy, hash, FIT_IGNORE_PROP, 1))
		return 14;
	if (fit_image_hash_get_ignore(copy, hash, &ignore) || !ignore)
		return 16;
	node = fdt_path_offset(copy, "/images/kernel");
	data = fdt_getprop(copy, node, "data", &len);
	ret = fit_image_verify_with_data(copy, node, NULL, data, len);
	if (ret != 0)
		return 15;
	free(copy);
	free(orig);
	puts("FIT hash tests passed: valid kernel/FDT, missing hash, "
	     "mismatched hash and mismatch with ignore flag rejected");
	return 0;
}
'''
compile_and_run(args, p, include=(args.host_prefix / 'include',), libraries=('fdt', 'crypto'))
