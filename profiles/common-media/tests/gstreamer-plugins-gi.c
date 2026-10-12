/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted). Resolve installed typelib records to real GTypes.
 */
#include <gst/gst.h>
#include <girepository.h>
#include <stdio.h>

int
main(int argc, char **argv)
{
	static const char *names[] = {
		"GstAllocators", "GstApp", "GstAudio", "GstPbutils", "GstRtp",
		"GstRtsp", "GstSdp", "GstTag", "GstVideo", "GstAnalytics",
		"GstBadAudio", "GstCodecParsers", "GstCodecs", "GstDxva",
		"GstInsertBin", "GstMpegts", "GstPlay", "GstPlayer",
		"GstTranscoder", "GstWebRTC"
	};
	static const struct { const char *ns, *name; } types[] = {
		{ "GstVideo", "VideoInfo" }, { "GstPbutils", "Discoverer" },
		{ "GstInsertBin", "InsertBin" }, { "GstPlay", "Play" },
		{ "GstPlayer", "Player" }, { "GstTranscoder", "Transcoder" }
	};
	gst_init(&argc, &argv);
	GIRepository *repo = g_irepository_get_default();
	for (size_t i = 0; i < G_N_ELEMENTS(names); i++) {
		GError *error = NULL;
		if (g_irepository_require(repo, names[i], "1.0", 0, &error) == NULL) {
			fprintf(stderr, "%s: %s\n", names[i], error->message);
			g_error_free(error);
			return 1;
		}
		if (g_irepository_get_n_infos(repo, names[i]) < 1) return 1;
		printf("loaded %s\n", names[i]);
	}
	for (size_t i = 0; i < G_N_ELEMENTS(types); i++) {
		GIBaseInfo *info = g_irepository_find_by_name(repo, types[i].ns,
		    types[i].name);
		if (info == NULL) return 1;
		GType type = g_registered_type_info_get_g_type((GIRegisteredTypeInfo *)info);
		g_base_info_unref(info);
		if (type == G_TYPE_INVALID || g_type_name(type) == NULL) return 1;
		printf("resolved %s.%s -> %s\n", types[i].ns, types[i].name,
		    g_type_name(type));
	}
	puts("PASS: 20 installed typelibs and six actual library GTypes");
	return 0;
}
