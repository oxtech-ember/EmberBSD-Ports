/* Test the actual libproxy PAC download function with an owned local file.
 * Origin: EmberBSD (AI-assisted).
 * SPDX-License-Identifier: BSD-2-Clause
 */
#ifndef EMBERBSD_LIBPROXY_MANAGER_SOURCE
#error "Set EMBERBSD_LIBPROXY_MANAGER_SOURCE to the actual px-manager.c"
#endif
#include EMBERBSD_LIBPROXY_MANAGER_SOURCE
#ifndef HAVE_CURL
#error "Use the configured curl-enabled libproxy source"
#endif
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int
main(void)
{
	static const unsigned char expected[] =
	    "function FindProxyForURL(url, host) { return 'DIRECT'; }\n";
	PxManager manager = { 0 };
	GBytes *bytes = NULL;
	GError *error = NULL;
	char name[] = "libproxy-pac-XXXXXX";
	char *absolute = NULL, *uri = NULL, *prefixed = NULL;
	const char *inputs[2];
	const void *data;
	gsize size;
	int fd = -1, result = 1, initialized = 0, created = 0;
	unsigned int i;

	if (curl_global_init(CURL_GLOBAL_DEFAULT) != CURLE_OK)
		goto out;
	initialized = 1;
	fd = g_mkstemp(name);
	if (fd == -1)
		goto out;
	created = 1;
	if (close(fd) == -1) {
		fd = -1;
		goto out;
	}
	fd = -1;
	if (!g_file_set_contents(name, (const char *)expected,
	    sizeof(expected) - 1, &error))
		goto out;
	absolute = g_canonicalize_filename(name, NULL);
	uri = g_filename_to_uri(absolute, NULL, &error);
	if (uri == NULL)
		goto out;
	prefixed = g_strconcat("pac+", uri, NULL);
	inputs[0] = uri;
	inputs[1] = prefixed;
	for (i = 0; i < 2; i++) {
		bytes = px_manager_pac_download(&manager, inputs[i]);
		if (bytes == NULL)
			goto out;
		data = g_bytes_get_data(bytes, &size);
		if (size != sizeof(expected) - 1 ||
		    memcmp(data, expected, sizeof(expected) - 1) != 0)
			goto out;
		g_bytes_unref(bytes);
		bytes = NULL;
	}
	puts("PASS: actual PAC downloader preserves both file URI payloads");
	result = 0;
out:
	if (result != 0)
		fprintf(stderr, "PAC download test failed%s%s\n",
		    error != NULL ? ": " : "", error != NULL ? error->message : "");
	if (bytes != NULL)
		g_bytes_unref(bytes);
	if (manager.curl != NULL)
		curl_easy_cleanup(manager.curl);
	if (initialized)
		curl_global_cleanup();
	g_clear_error(&error);
	g_free(prefixed);
	g_free(uri);
	g_free(absolute);
	if (fd != -1)
		(void)close(fd);
	if (created && unlink(name) == -1)
		result = 1;
	return result;
}
