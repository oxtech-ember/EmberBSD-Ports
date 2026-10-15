/* SPDX-License-Identifier: BSD-2-Clause */
/* No GPU descriptor is opened. Check a real libdrm failure with and without preload. */
#include <errno.h>
#include <stdio.h>
#include <xf86drm.h>
#include <v3d_drm.h>

int
main(void)
{
	struct drm_v3d_create_bo create = { .size = 4096 };
	int result, error;

	errno = 0;
	result = drmIoctl(-1, DRM_IOCTL_V3D_CREATE_BO, &create);
	error = errno;
	printf("drmIoctl invalid-fd ret=%d errno=%d size=%u\n",
	    result, error, create.size);
	return (result == -1 && error == EBADF && create.size == 4096 ? 0 : 1);
}
