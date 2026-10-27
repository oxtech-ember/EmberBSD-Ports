/* SPDX-License-Identifier: BSD-2-Clause
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 */
#include <hfs.h>
#include <stdio.h>
#include <string.h>

int
main(int argc, char **argv)
{
	hfsvol *volume;
	hfsfile *file;
	char buffer[4] = {0};

	if (argc != 2 || hfs_format(argv[1], 0, 0, "Test", 0, NULL) < 0)
		return 1;
	volume = hfs_mount(argv[1], 0, HFS_MODE_RDWR);
	if (volume == NULL)
		return 2;
	file = hfs_create(volume, "sample", "TEXT", "ttxt");
	if (file == NULL || hfs_write(file, "abc", 3) != 3 ||
	    hfs_setfork(file, 1) < 0 || hfs_write(file, "xyz", 3) != 3 ||
	    hfs_close(file) < 0)
		return 3;
	file = hfs_open(volume, "sample");
	if (file == NULL || hfs_read(file, buffer, 3) != 3 ||
	    memcmp(buffer, "abc", 3) != 0 || hfs_setfork(file, 1) < 0 ||
	    hfs_read(file, buffer, 3) != 3 || memcmp(buffer, "xyz", 3) != 0)
		return 4;
	return hfs_close(file) < 0 || hfs_umount(volume) < 0;
}
