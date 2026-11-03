/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Exercise the packaged SVG renderer on target. */
#include <cairo.h>
#include <librsvg/rsvg.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef LIBRSVG_CSS_ONLY
#include <sys/stat.h>
#include <sys/wait.h>

#include <fontconfig/fontconfig.h>
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <girepository/girepository.h>

#include <errno.h>
#include <fcntl.h>

#include "librsvg-fixtures.h"
#endif

#ifndef LIBRSVG_CSS_ONLY
static const char svg[] =
    "<svg xmlns='http://www.w3.org/2000/svg' width='32' height='16'>"
    "<rect width='16' height='16' fill='#ff0000'/>"
    "<rect x='16' width='16' height='16' fill='#00ff00'/>"
    "<circle cx='16' cy='8' r='4' fill='#0000ff'/></svg>";
#endif
static const char invalid_svg[] = "<svg><broken";
static const char css_svg[] =
	"<svg xmlns='http://www.w3.org/2000/svg' width='40' height='10'>"
	"<style>rect { fill: #ff0000; }"
	":lang(fr) > rect { fill: rgb(0% 100% 0%); }"
	"#before + g > rect { fill: #00ffff; }"
	".hsl { fill: hsl(240 100% 50%); }</style>"
	"<rect id='before' width='10' height='10'/>"
	"<g><rect x='10' width='10' height='10'/></g>"
	"<g xml:lang='fr'><rect x='20' width='10' height='10'/></g>"
	"<rect class='hsl' x='30' width='10' height='10'/></svg>";
static const char unknown_pseudo_svg[] =
	"<svg xmlns='http://www.w3.org/2000/svg' width='4' height='4'>"
	"<style>rect { fill: red; }\n\n"
	"rect:unknown-rsvg-pseudo { fill: blue; }</style>"
	"<rect width='4' height='4'/></svg>";
static const char unknown_at_rule_svg[] =
	"<svg xmlns='http://www.w3.org/2000/svg' width='4' height='4'>"
	"<style>@unknown-rsvg-rule value;\nrect { fill: red; }</style>"
	"<rect width='4' height='4'/></svg>";

static void
check(int condition, const char *message)
{

	if (!condition) {
		fprintf(stderr, "FAIL: %s\n", message);
		exit(1);
	}
}

#ifndef LIBRSVG_CSS_ONLY
static void
write_file(const char *name, const void *data, size_t size, mode_t mode)
{
	const unsigned char *p = data;
	ssize_t written;
	int fd;

	fd = open(name, O_WRONLY | O_CREAT | O_EXCL, mode);
	check(fd >= 0, "create temporary fixture");
	while (size != 0) {
		written = write(fd, p, size);
		check(written > 0, "write temporary fixture");
		p += written;
		size -= (size_t)written;
	}
	check(close(fd) == 0, "close temporary fixture");
}
#endif

#ifndef LIBRSVG_CSS_ONLY
static int
run(char *const args[], const char *output)
{
	pid_t pid;
	int status, fd;

	pid = fork();
	check(pid >= 0, "fork packaged utility");
	if (pid == 0) {
		if (output != NULL) {
			fd = open(output, O_WRONLY | O_CREAT | O_TRUNC, 0600);
			if (fd < 0 || dup2(fd, STDOUT_FILENO) < 0)
				_exit(125);
			close(fd);
		}
		execv(args[0], args);
		_exit(126);
	}
	check(waitpid(pid, &status, 0) == pid, "wait for packaged utility");
	return WIFEXITED(status) ? WEXITSTATUS(status) : 127;
}
#endif

static uint32_t
pixel(cairo_surface_t *surface, int x, int y)
{
	const unsigned char *data;

	check(cairo_surface_status(surface) == CAIRO_STATUS_SUCCESS, "Cairo surface");
	cairo_surface_flush(surface);
	data = cairo_image_surface_get_data(surface);
	return *(const uint32_t *)(data + y * cairo_image_surface_get_stride(surface) + x * 4);
}

#ifndef LIBRSVG_CSS_ONLY
static void
check_surface(cairo_surface_t *surface)
{

	check(cairo_image_surface_get_width(surface) == 32 &&
	    cairo_image_surface_get_height(surface) == 16, "SVG dimensions");
	check(pixel(surface, 4, 4) == 0xffff0000U &&
	    pixel(surface, 28, 4) == 0xff00ff00U &&
	    pixel(surface, 16, 8) == 0xff0000ffU, "SVG RGB reference pixels");
}
#endif

static cairo_surface_t *
render(const char *text, size_t length, int width, int height)
{
	RsvgHandle *handle;
	RsvgRectangle viewport = { 0, 0, width, height };
	cairo_surface_t *surface;
	cairo_t *cr;
	GError *error = NULL;

	handle = rsvg_handle_new_from_data((const guint8 *)text, length, &error);
	if (error != NULL)
		fprintf(stderr, "%s\n", error->message);
	check(handle != NULL && error == NULL, "parse SVG");
	surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, width, height);
	cr = cairo_create(surface);
	check(rsvg_handle_render_document(handle, cr, &viewport, &error), "render SVG document");
	check(error == NULL && cairo_status(cr) == CAIRO_STATUS_SUCCESS, "render without error");
	cairo_destroy(cr);
	g_object_unref(handle);
	return surface;
}

static void
check_css_diagnostic(const char *text, size_t text_length,
	const char *boundary, const char *name, const char *name_message)
{
	char output[4096];
	cairo_surface_t *surface;
	FILE *capture;
	size_t length;
	int capture_fd, close_status;
	int saved_stdout;

	check(setenv("RSVG_LOG", "1", 1) == 0, "enable librsvg diagnostics");
	capture = tmpfile();
	check(capture != NULL, "create diagnostic capture");
	check(fflush(stdout) == 0, "flush stdout before capture");
	capture_fd = fileno(capture);
	if (capture_fd < 0) {
		(void)fprintf(stderr, "could not get diagnostic capture descriptor\n");
		(void)fclose(capture);
		abort();
	}
	saved_stdout = dup(STDOUT_FILENO);
	check(saved_stdout >= 0, "save stdout");
	check(dup2(capture_fd, STDOUT_FILENO) == STDOUT_FILENO,
	    "capture librsvg diagnostics");
	surface = render(text, text_length, 4, 4);
	cairo_surface_destroy(surface);
	check(fflush(stdout) == 0, "flush captured diagnostics");
	check(dup2(saved_stdout, STDOUT_FILENO) == STDOUT_FILENO,
	    "restore stdout");
	check(close(saved_stdout) == 0, "close saved stdout");
	check(fseek(capture, 0, SEEK_SET) == 0, "rewind diagnostic capture");
	length = fread(output, 1, sizeof(output) - 1, capture);
	check(!ferror(capture) && length < sizeof(output) - 1,
	    "bounded diagnostic output");
	output[length] = '\0';
	close_status = fclose(capture);
	check(close_status == 0, "close diagnostic capture");
	if (strstr(output, boundary) == NULL || strstr(output, name) == NULL) {
		fprintf(stderr,
		    "Expected CSS diagnostic boundary '%s' and name '%s'; captured %zu bytes:\n",
		    boundary, name, length);
		(void)fwrite(output, 1, length, stderr);
		(void)fputc('\n', stderr);
	}
	check(strstr(output, boundary) != NULL,
	    "CSS diagnostic retains rule boundary");
	check(strstr(output, name) != NULL, name_message);
}

static void
check_css_only(void)
{
	cairo_surface_t *surface;
	RsvgHandle *bad;
	GError *error = NULL;
	uint32_t value;

	check(setenv("RSVG_LOG", "1", 1) == 0, "enable librsvg diagnostics");
	surface = render(css_svg, sizeof(css_svg) - 1, 40, 10);
	value = pixel(surface, 5, 5);
	check(value == 0xffff0000U, "CSS base selector red pixel");
	check(pixel(surface, 15, 5) == 0xff00ffffU,
	    "CSS ID, adjacent-sibling and child selectors produce cyan pixel");
	check(pixel(surface, 25, 5) == 0xff00ff00U,
	    "CSS :lang selector green pixel");
	check(pixel(surface, 35, 5) == 0xff0000ffU,
	    "CSS HSL color blue pixel");
	cairo_surface_destroy(surface);
	check_css_diagnostic(unknown_pseudo_svg, sizeof(unknown_pseudo_svg) - 1,
	    "line: 2", "unknown-rsvg-pseudo",
	    "CSS diagnostic retains unsupported pseudo name");
	check_css_diagnostic(unknown_at_rule_svg, sizeof(unknown_at_rule_svg) - 1,
	    "line: 0", "unknown-rsvg-rule",
	    "CSS diagnostic retains unsupported at-rule name");
	bad = rsvg_handle_new_from_data((const guint8 *)invalid_svg,
	    sizeof(invalid_svg) - 1, &error);
	check(bad == NULL && error != NULL, "malformed SVG is rejected by C API");
	g_clear_error(&error);
	puts("PASS: installed C API CSS colors, :lang, diagnostic boundaries/names, malformed SVG");
}

#ifndef LIBRSVG_CSS_ONLY
static void
check_metadata(void)
{
	GIRepository *repository = gi_repository_new();
	GITypelib *typelib;
	GIBaseInfo *info;
	GIFunctionInfo *method;
	GIArgument result = { 0 };
	GError *error = NULL;
	GBytes *bytes;
	size_t i;

	for (i = 0; i < G_N_ELEMENTS(typelibs); i++) {
		bytes = g_bytes_new_static(typelibs[i].start, typelibs[i].end - typelibs[i].start);
		typelib = gi_typelib_new_from_bytes(bytes, &error);
		g_bytes_unref(bytes);
		check(typelib != NULL && error == NULL, "parse packaged typelib");
		check(gi_repository_load_typelib(repository, typelib,
		    GI_REPOSITORY_LOAD_FLAG_LAZY, &error) != NULL, "load packaged namespace");
		gi_typelib_unref(typelib);
	}
	info = gi_repository_find_by_name(repository, "Rsvg", "Handle");
	check(info != NULL && GI_IS_OBJECT_INFO(info), "Rsvg Handle metadata");
	method = gi_object_info_find_method(GI_OBJECT_INFO(info), "new");
	check(method != NULL && strcmp(gi_function_info_get_symbol(method), "rsvg_handle_new") == 0,
	    "Rsvg constructor symbol");
	check(gi_function_info_invoke(method, NULL, 0, NULL, 0, &result, &error),
	    "invoke Rsvg constructor through packaged metadata");
	check(RSVG_IS_HANDLE(result.v_pointer), "introspection returned an RsvgHandle");
	g_object_unref(result.v_pointer);
	gi_base_info_unref(GI_BASE_INFO(method));
	gi_base_info_unref(info);
	g_object_unref(repository);
}
#endif

#ifdef LIBRSVG_CSS_ONLY
int
main(void)
{
	check_css_only();
	return 0;
}
#else
int
main(int argc, char **argv)
{
	char cwd[4096], loader[4096], cache[4096];
	char *query_args[] = { "./query-loaders", loader, NULL };
	char *cli_args[] = { "./rsvg-convert", "-o", "cli.png", "input.svg", NULL };
	char *bad_args[] = { "./rsvg-convert", "-o", "bad.png", "bad.svg", NULL };
	char *version_args[] = { "./rsvg-convert", "--version", NULL };
	char *mime_args[] = { "./update-mime-database", "mime", NULL };
	cairo_surface_t *surface;
	GdkPixbuf *pixbuf;
	GError *error = NULL;
	RsvgHandle *bad;
	FcConfig *fonts;
	const unsigned char *p;
	uint32_t value;
	unsigned int cycle, i, ink;
	int stride, channels;
	int loader_only = argc == 2 && strcmp(argv[1], "--loader-only") == 0;
	int css_only = argc == 2 && strcmp(argv[1], "--css-only") == 0;

	check(argc == 1 || loader_only || css_only,
	    "usage: librsvg-package [--loader-only|--css-only]");
	if (css_only) {
		check_css_only();
		return 0;
	}

	check(getcwd(cwd, sizeof(cwd)) != NULL, "temporary working directory");
	check(snprintf(loader, sizeof(loader), "%s/svg-loader.so", cwd) < (int)sizeof(loader), "loader path");
	check(snprintf(cache, sizeof(cache), "%s/loaders.cache", cwd) < (int)sizeof(cache), "cache path");
	check(mkdir("mime", 0700) == 0 && mkdir("mime/packages", 0700) == 0,
	    "private MIME directories");
	for (i = 0; i < G_N_ELEMENTS(files); i++)
		write_file(files[i].name, files[i].start, files[i].end - files[i].start, files[i].mode);
	write_file("input.svg", svg, sizeof(svg) - 1, 0600);
	write_file("bad.svg", invalid_svg, sizeof(invalid_svg) - 1, 0600);
	check(run(query_args, "loaders.cache") == 0, "query the packaged SVG module");
	check(setenv("GDK_PIXBUF_MODULE_FILE", cache, 1) == 0, "private loader cache");
	check(setenv("XDG_DATA_HOME", cwd, 1) == 0 &&
	    setenv("XDG_DATA_DIRS", cwd, 1) == 0, "private MIME search paths");
	check(run(mime_args, NULL) == 0, "generate the packaged MIME database");
	if (loader_only) {
		pixbuf = gdk_pixbuf_new_from_file("input.svg", &error);
		if (error != NULL)
			fprintf(stderr, "SVG loader: %s (%s:%d)\n", error->message,
			    g_quark_to_string(error->domain), error->code);
		check(pixbuf != NULL && error == NULL, "dynamic GdkPixbuf SVG loader");
		g_object_unref(pixbuf);
		puts("PASS: isolated SVG loader");
		return 0;
	}
	check(run(version_args, NULL) == 0, "packaged CLI version");
	fonts = FcConfigCreate();
	check(fonts != NULL && FcConfigAppFontAddFile(fonts, (const FcChar8 *)"Ahem.ttf") &&
	    FcConfigSetCurrent(fonts), "private upstream test font");
	for (cycle = 0; cycle < 4; cycle++) {
		surface = render(svg, sizeof(svg) - 1, 32, 16);
		check_surface(surface);
		cairo_surface_destroy(surface);
		check(run(cli_args, NULL) == 0, "packaged rsvg-convert");
		surface = cairo_image_surface_create_from_png("cli.png");
		check_surface(surface);
		cairo_surface_destroy(surface);
		pixbuf = gdk_pixbuf_new_from_file("input.svg", &error);
		if (error != NULL)
			fprintf(stderr, "SVG loader: %s (%s:%d)\n", error->message,
			    g_quark_to_string(error->domain), error->code);
		check(pixbuf != NULL && error == NULL, "dynamic GdkPixbuf SVG loader");
		check(gdk_pixbuf_get_width(pixbuf) == 32 && gdk_pixbuf_get_height(pixbuf) == 16, "pixbuf dimensions");
		stride = gdk_pixbuf_get_rowstride(pixbuf);
		channels = gdk_pixbuf_get_n_channels(pixbuf);
		p = gdk_pixbuf_get_pixels(pixbuf);
		check(p[4 * stride + 4 * channels] == 255 && p[4 * stride + 4 * channels + 1] == 0 &&
		    p[4 * stride + 28 * channels + 1] == 255 && p[8 * stride + 16 * channels + 2] == 255,
		    "dynamic loader RGB reference pixels");
		g_object_unref(pixbuf);
		surface = render(avif_svg, sizeof(avif_svg) - 1, 20, 10);
		value = pixel(surface, 5, 5);
		check((value >> 24) == 255 && ((value >> 16) & 255) >= 124 &&
		    ((value >> 16) & 255) <= 128 && ((value >> 8) & 255) >= 253 &&
		    (value & 255) <= 4 && pixel(surface, 15, 5) == 0, "embedded AVIF reference pixels");
		cairo_surface_destroy(surface);
		surface = render(text_svg, sizeof(text_svg) - 1, 32, 16);
		ink = 0;
		for (i = 0; i < 32 * 16; i++)
			if (pixel(surface, i % 32, i / 32) != 0)
				ink++;
		check(ink >= 32 && ink <= 400, "Pango text renders with the bundled font");
		cairo_surface_destroy(surface);
		check_metadata();
		bad = rsvg_handle_new_from_data((const guint8 *)invalid_svg, sizeof(invalid_svg) - 1, &error);
		check(bad == NULL && error != NULL, "malformed SVG is rejected");
		g_clear_error(&error);
		printf("cycle %u: C API, CLI PNG, dynamic pixbuf, AVIF, text and GIR invoke PASS\n", cycle + 1);
	}
	check(run(bad_args, NULL) == 1, "CLI rejects malformed SVG with exit 1");
	FcConfigDestroy(fonts);
	puts("PASS: packaged librsvg features across four target lifecycles; malformed SVG refused");
	return 0;
}
#endif
