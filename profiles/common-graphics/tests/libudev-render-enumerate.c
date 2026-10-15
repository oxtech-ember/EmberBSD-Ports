/* SPDX-License-Identifier: BSD-2-Clause */
/* Exercise the public libudev API with KWin's render-node filters. */
#include <sys/stat.h>

#include <errno.h>
#include <fcntl.h>
#include <fnmatch.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <libudev.h>

int
main(void)
{
	unsigned int cycle;

	for (cycle = 1; cycle <= 4; cycle++) {
		struct udev *context;
		struct udev_enumerate *enumerator;
		struct udev_list_entry *entry;
		unsigned int nodes = 0, opened = 0;

		context = udev_new();
		if (context == NULL)
			return (1);
		enumerator = udev_enumerate_new(context);
		if (enumerator == NULL) {
			udev_unref(context);
			return (1);
		}
		if (udev_enumerate_add_match_subsystem(enumerator, "drm") < 0 ||
		    udev_enumerate_add_match_sysname(enumerator,
		    "renderD[1-2][0-9][0-9]") < 0 ||
		    udev_enumerate_scan_devices(enumerator) < 0) {
			fprintf(stderr, "libudev enumeration failed\n");
			udev_enumerate_unref(enumerator);
			udev_unref(context);
			return (1);
		}
		udev_list_entry_foreach(entry,
		    udev_enumerate_get_list_entry(enumerator)) {
			struct udev_device *device;
			struct stat st;
			const char *path, *subsystem, *sysname, *devnode;
			int fd, saved_errno;

			path = udev_list_entry_get_name(entry);
			device = udev_device_new_from_syspath(context, path);
			if (device == NULL) {
				fprintf(stderr, "cannot create device: %s\n", path);
				udev_enumerate_unref(enumerator);
				udev_unref(context);
				return (1);
			}
			subsystem = udev_device_get_subsystem(device);
			sysname = udev_device_get_sysname(device);
			devnode = udev_device_get_devnode(device);
			if (subsystem == NULL || strcmp(subsystem, "drm") != 0 ||
			    sysname == NULL || fnmatch("renderD[1-2][0-9][0-9]",
			    sysname, 0) != 0 || devnode == NULL ||
			    stat(devnode, &st) != 0 || !S_ISCHR(st.st_mode) ||
			    st.st_rdev != udev_device_get_devnum(device)) {
				fprintf(stderr, "invalid render-node metadata: %s\n", path);
				udev_device_unref(device);
				udev_enumerate_unref(enumerator);
				udev_unref(context);
				return (1);
			}
			nodes++;
			fd = open(devnode, O_RDWR | O_CLOEXEC);
			saved_errno = fd < 0 ? errno : 0;
			if (fd >= 0) {
				opened++;
				close(fd);
			}
			printf("cycle=%u node=%s subsystem=%s sysname=%s open_errno=%d\n",
			    cycle, devnode, subsystem, sysname, saved_errno);
			udev_device_unref(device);
		}
		udev_enumerate_unref(enumerator);
		udev_unref(context);
		printf("cycle=%u classified=%u opened=%u\n", cycle, nodes, opened);
		if (nodes == 0 || opened == 0)
			return (1);
	}
	return (0);
}
