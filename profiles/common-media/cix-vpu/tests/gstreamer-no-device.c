/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Load the actual V4L2 plugin without M2M. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gst/gst.h>

int
main(int argc, char **argv)
{
	GError *error = NULL;
	GstPlugin *plugin;
	GstElementFactory *factory;
	GList *features, *entry;
	int result = EXIT_SUCCESS;

	if (argc != 2) {
		fprintf(stderr, "Usage: gstreamer-no-device ABSOLUTE_PLUGIN\n");
		return EXIT_FAILURE;
	}
	gst_init(NULL, NULL);
	plugin = gst_plugin_load_file(argv[1], &error);
	if (plugin == NULL) {
		fprintf(stderr, "Plugin load failed: %s\n",
		    error != NULL ? error->message : "unknown error");
		g_clear_error(&error);
		gst_deinit();
		return EXIT_FAILURE;
	}
	features = gst_registry_get_feature_list_by_plugin(gst_registry_get(),
	    gst_plugin_get_name(plugin));
	for (entry = features; entry != NULL; entry = entry->next) {
		const char *name = gst_plugin_feature_get_name(entry->data);
		if (strstr(name, "h265") != NULL) {
			fprintf(stderr, "Unexpected H.265 hardware factory: %s\n", name);
			result = EXIT_FAILURE;
		}
	}
	gst_plugin_feature_list_free(features);
	factory = gst_element_factory_find("v4l2src");
	if (factory == NULL)
		result = EXIT_FAILURE;
	else
		gst_object_unref(factory);
	gst_object_unref(plugin);
	gst_deinit();
	if (result == EXIT_SUCCESS)
		puts("PASS: actual V4L2 plugin loads; absent hardware creates no H.265 factory");
	return result;
}
