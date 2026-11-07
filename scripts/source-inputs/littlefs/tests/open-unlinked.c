/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
/* Regression: open CTZ data remains allocated after unlink/overwrite. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "lfs.h"

#define BLOCK_SIZE 512
#define BLOCK_COUNT 48
#define FLASH_SIZE (BLOCK_SIZE * BLOCK_COUNT)
#define VICTIM_SIZE 4096
#define PRESSURE_SIZE 1536

struct flash {
	uint8_t bytes[FLASH_SIZE];
};

static int
flash_read(const struct lfs_config *cfg, lfs_block_t block, lfs_off_t off,
    void *buffer, lfs_size_t size)
{
	struct flash *flash = cfg->context;
	size_t pos = (size_t)block * BLOCK_SIZE + off;

	if (pos + size > sizeof(flash->bytes))
		return LFS_ERR_IO;
	memcpy(buffer, flash->bytes + pos, size);
	return 0;
}

static int
flash_prog(const struct lfs_config *cfg, lfs_block_t block, lfs_off_t off,
    const void *buffer, lfs_size_t size)
{
	struct flash *flash = cfg->context;
	const uint8_t *src = buffer;
	size_t pos = (size_t)block * BLOCK_SIZE + off;

	if (pos + size > sizeof(flash->bytes))
		return LFS_ERR_IO;
	for (size_t i = 0; i < size; i++) {
		if ((flash->bytes[pos + i] & src[i]) != src[i])
			return LFS_ERR_IO;
		flash->bytes[pos + i] &= src[i];
	}
	return 0;
}

static int
flash_erase(const struct lfs_config *cfg, lfs_block_t block)
{
	struct flash *flash = cfg->context;
	size_t pos = (size_t)block * BLOCK_SIZE;

	if (pos + BLOCK_SIZE > sizeof(flash->bytes))
		return LFS_ERR_IO;
	memset(flash->bytes + pos, 0xff, BLOCK_SIZE);
	return 0;
}

static int
flash_sync(const struct lfs_config *cfg)
{
	(void)cfg;
	return 0;
}

static void
fill_pattern(uint8_t *data, size_t size, uint8_t seed)
{
	for (size_t i = 0; i < size; i++)
		data[i] = (uint8_t)(seed + i * 37u + i / 11u);
}

static int
write_file(lfs_t *lfs, const char *path, const uint8_t *data, size_t size)
{
	lfs_file_t file;
	int err = lfs_file_open(lfs, &file, path, LFS_O_WRONLY | LFS_O_CREAT | LFS_O_TRUNC);
	if (err)
		return err;
	lfs_ssize_t n = lfs_file_write(lfs, &file, data, size);
	if (n != (lfs_ssize_t)size)
		err = n < 0 ? (int)n : LFS_ERR_IO;
	if (!err)
		err = lfs_file_sync(lfs, &file);
	int close_err = lfs_file_close(lfs, &file);
	return err ? err : close_err;
}

static int
read_matches(lfs_t *lfs, lfs_file_t *file, const uint8_t *expected, size_t size)
{
	uint8_t buffer[VICTIM_SIZE];
	if (lfs_file_rewind(lfs, file) != 0)
		return 0;
	lfs_ssize_t n = lfs_file_read(lfs, file, buffer, size);
	return n == (lfs_ssize_t)size && memcmp(buffer, expected, size) == 0;
}

static int
scenario(const char *mode)
{
	struct flash flash;
	memset(&flash, 0xff, sizeof(flash));
	struct lfs_config cfg = {
		.context = &flash,
		.read = flash_read,
		.prog = flash_prog,
		.erase = flash_erase,
		.sync = flash_sync,
		.read_size = 16,
		.prog_size = 16,
		.block_size = BLOCK_SIZE,
		.block_count = BLOCK_COUNT,
		.block_cycles = -1,
		.cache_size = 64,
		.lookahead_size = 16,
	};
	lfs_t lfs;
	int err = lfs_format(&lfs, &cfg);
	if (err) {
		fprintf(stderr, "format failed: %d\n", err);
		return 2;
	}
	err = lfs_mount(&lfs, &cfg);
	if (err) {
		fprintf(stderr, "mount failed: %d\n", err);
		return 2;
	}

	uint8_t victim[VICTIM_SIZE];
	fill_pattern(victim, sizeof(victim), 0x29);
	if (strcmp(mode, "overwrite") == 0) {
		err = write_file(&lfs, "/target", victim, sizeof(victim));
	} else {
		err = write_file(&lfs, "/victim", victim, sizeof(victim));
	}
	if (err) {
		fprintf(stderr, "initial write failed: %d\n", err);
		return 2;
	}

	lfs_file_t open_victim;
	const char *victim_path = strcmp(mode, "overwrite") == 0 ? "/target" : "/victim";
	err = lfs_file_open(&lfs, &open_victim, victim_path, LFS_O_RDONLY);
	if (err) {
		fprintf(stderr, "open victim failed: %d\n", err);
		return 2;
	}
	if (strcmp(mode, "overwrite") == 0) {
		uint8_t replacement[VICTIM_SIZE];
		fill_pattern(replacement, sizeof(replacement), 0xb3);
		err = write_file(&lfs, "/replacement", replacement, sizeof(replacement));
		if (!err)
			err = lfs_rename(&lfs, "/replacement", "/target");
	} else {
		err = lfs_remove(&lfs, "/victim");
	}
	if (err) {
		fprintf(stderr, "unlink/overwrite operation failed: %d\n", err);
		return 2;
	}

	/* Force allocator and metadata GC to reuse blocks while the old fd is open. */
	uint8_t pressure[PRESSURE_SIZE];
	fill_pattern(pressure, sizeof(pressure), 0x61);
	for (unsigned i = 0; i < 128; i++) {
		char path[24];
		(void)snprintf(path, sizeof(path), "/pressure%03u", i);
		fill_pattern(pressure, sizeof(pressure), (uint8_t)i);
		err = write_file(&lfs, path, pressure, sizeof(pressure));
		if (err == LFS_ERR_NOSPC)
			break;
		if (err) {
			fprintf(stderr, "pressure write failed: %d\n", err);
			return 2;
		}
	}

	if (!read_matches(&lfs, &open_victim, victim, sizeof(victim))) {
		fprintf(stderr, "OPEN_FILE_DATA_MISMATCH mode=%s\n", mode);
		return 1;
	}
	lfs_ssize_t open_blocks = lfs_fs_size(&lfs);
	if (open_blocks < 0) {
		fprintf(stderr, "filesystem size while open failed: %d\n", (int)open_blocks);
		return 2;
	}
	if (lfs_file_close(&lfs, &open_victim) != 0) {
		fprintf(stderr, "close victim failed\n");
		return 2;
	}
	lfs_ssize_t closed_blocks = lfs_fs_size(&lfs);
	if (closed_blocks < 0 || closed_blocks >= open_blocks) {
		fprintf(stderr, "orphan blocks not reclaimed after close: open=%d closed=%d\n",
		    (int)open_blocks, (int)closed_blocks);
		return 1;
	}
	if (lfs_unmount(&lfs) != 0) {
		fprintf(stderr, "unmount failed\n");
		return 2;
	}
	puts("open-file preservation passed");
	return 0;
}

static int
inline_sync(void)
{
	struct flash flash;
	memset(&flash, 0xff, sizeof(flash));
	struct lfs_config cfg = {
		.context = &flash, .read = flash_read, .prog = flash_prog,
		.erase = flash_erase, .sync = flash_sync,
		.read_size = 16, .prog_size = 16, .block_size = BLOCK_SIZE,
		.block_count = BLOCK_COUNT, .block_cycles = -1,
		.cache_size = 64, .lookahead_size = 16,
	};
	lfs_t lfs;
	if (lfs_format(&lfs, &cfg) || lfs_mount(&lfs, &cfg))
		return 2;
	const uint8_t text[] = "inline data survives sync and unlink";
	lfs_file_t file;
	if (lfs_file_open(&lfs, &file, "/inline", LFS_O_WRONLY | LFS_O_CREAT) ||
	    lfs_file_write(&lfs, &file, text, sizeof(text)) != sizeof(text) ||
	    lfs_file_sync(&lfs, &file) || lfs_file_close(&lfs, &file))
		return 2;
	if (lfs_file_open(&lfs, &file, "/inline", LFS_O_RDONLY) ||
	    lfs_remove(&lfs, "/inline"))
		return 2;
	uint8_t got[sizeof(text)];
	int ok = lfs_file_read(&lfs, &file, got, sizeof(got)) == sizeof(got) &&
	    memcmp(got, text, sizeof(text)) == 0;
	if (lfs_file_close(&lfs, &file) || lfs_unmount(&lfs))
		return 2;
	if (!ok) {
		fputs("INLINE_SYNC_DATA_MISMATCH\n", stderr);
		return 1;
	}
	puts("inline sync/unlink passed");
	return 0;
}

int
main(int argc, char **argv)
{
	if (argc != 2) {
		fprintf(stderr, "usage: %s unlink|overwrite|inline-sync\n", argv[0]);
		return 2;
	}
	if (strcmp(argv[1], "inline-sync") == 0)
		return inline_sync();
	if (strcmp(argv[1], "unlink") != 0 && strcmp(argv[1], "overwrite") != 0)
		return 2;
	return scenario(argv[1]);
}
