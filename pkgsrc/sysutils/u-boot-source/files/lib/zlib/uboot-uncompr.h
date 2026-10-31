/* SPDX-License-Identifier: GPL-2.0+ */
/* Supply the allocators required by upstream zlib's freestanding mode. */
#include <stddef.h>
#include <u-boot/zlib.h>

static inline int uboot_uncompress_init(z_streamp stream)
{
	stream->zalloc = gzalloc;
	stream->zfree = gzfree;
	return inflateInit_(stream, ZLIB_VERSION, sizeof(z_stream));
}
#undef inflateInit
#define inflateInit(stream) uboot_uncompress_init(stream)
