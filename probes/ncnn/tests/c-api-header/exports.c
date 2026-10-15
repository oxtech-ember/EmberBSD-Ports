/* SPDX-License-Identifier: MIT */
#include <ncnn/c_api.h>

/* Definitions inherit the public declarations' default visibility. */
const char *
ncnn_version(void)
{
	return ("header-visibility-contract");
}

int
ncnn_version_number(void)
{
	return (20260526);
}
