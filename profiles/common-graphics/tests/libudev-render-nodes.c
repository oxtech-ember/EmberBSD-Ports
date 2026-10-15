/* SPDX-License-Identifier: BSD-2-Clause */
/* Compile the real classifier here to inspect its selected handler. */
#include <stdio.h>
#include "udev-utils.c"

#include "libudev-contract-stubs.h"

struct sample {
	const char *path;
	int drm;
	int kwin;
};

static const struct sample samples[] = {
	{ "/dev/dri/renderD128", 1, 1 },
	{ "/dev/dri/renderD129", 1, 1 },
	{ "/dev/dri/renderD191", 1, 1 },
	{ "/dev/dri/renderD255", 1, 1 },
	{ "/dev/dri/renderD299", 1, 1 },
	{ "/dev/dri/renderD0", 1, 0 },
	{ "/dev/dri/renderD99", 1, 0 },
	{ "/dev/dri/renderD300", 1, 0 },
	{ "/dev/dri/renderD1000", 1, 0 },
	{ "/dev/dri/renderD999999999999999999999999999999999999", 1, 0 },
	{ "/dev/dri/card0", 1, 0 },
	{ "/dev/dri/card12", 1, 0 },
	{ "", 0, 0 },
	{ "/dev/dri/renderD", 0, 0 },
	{ "/dev/dri/renderDa", 0, 0 },
	{ "/dev/dri/renderD128x", 0, 0 },
	{ "/dev/dri/renderD128/child", 0, 0 },
	{ "/dev/dri/renderD128/", 0, 0 },
	{ "/dev/dri/renderD128\n", 0, 0 },
	{ "/dev/dri/renderD-128", 0, 0 },
	{ "/dev/dri/renderD+128", 0, 0 },
	{ "/dev/dri/renderD 128", 0, 0 },
	{ "/dev/dri/renderD128.0", 0, 0 },
	{ "/dev/dri/renderd128", 0, 0 },
	{ "/dev/dri//renderD128", 0, 0 },
	{ "/dev/drm/renderD128", 0, 0 },
	{ "/dev/renderD128", 0, 0 },
	{ "dev/dri/renderD128", 0, 0 },
	{ "/other/dev/dri/renderD128", 0, 0 },
	{ "/dev/ukbd0", 0, 0 }
};

int
main(void)
{
	unsigned int cycle;
	size_t i;

	for (cycle = 0; cycle < 4; cycle++) {
		struct udev_filter_head filters;

		udev_filter_init(&filters);
		if (udev_filter_add(&filters, UDEV_FILTER_TYPE_SUBSYSTEM,
		    0, "drm", NULL) != 0 ||
		    udev_filter_add(&filters, UDEV_FILTER_TYPE_SYSNAME,
		    0, "renderD[1-2][0-9][0-9]", NULL) != 0)
			abort();
		for (i = 0; i < nitems(samples); i++) {
			const struct subsystem_config *config;
			const char *subsystem, *devtype;
			int drm, matched;

			subsystem = get_subsystem_by_syspath(samples[i].path, &devtype);
			drm = strcmp(subsystem, "drm") == 0;
			matched = udev_filter_match(NULL, &filters, samples[i].path);
			if (drm != samples[i].drm || matched != samples[i].kwin) {
				fprintf(stderr, "FAIL path=%s drm=%d kwin=%d expected=%d/%d\n",
				    samples[i].path, drm, matched, samples[i].drm,
				    samples[i].kwin);
				udev_filter_free(&filters);
				return (1);
			}
			config = get_subsystem_config_by_syspath(samples[i].path);
			if (drm && (config == NULL ||
			    config->create_handler != create_drm_handler || devtype == NULL ||
			    strcmp(devtype, "drm_minor") != 0))
				abort();
		}
		if (udev_filter_add(&filters, UDEV_FILTER_TYPE_SUBSYSTEM,
		    1, "drm", NULL) != 0 ||
		    udev_filter_match(NULL, &filters, "/dev/dri/renderD128"))
			abort();
		udev_filter_free(&filters);
	}
	printf("PASS: %zu path cases and DRM exclusion, four filter lifecycles\n",
	    nitems(samples));
	return (0);
}
