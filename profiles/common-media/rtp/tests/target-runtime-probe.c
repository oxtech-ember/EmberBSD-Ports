/* SPDX-License-Identifier: BSD-2-Clause
 * Copyright (c) 2026 EmberBSD contributors.
 * Origin: EmberBSD (AI-assisted).
 * Diagnostic only: target libc iconv and installed GLib/GIO error paths.
 */
#include <gio/gio.h>
#include <errno.h>
#include <iconv.h>
#include <langinfo.h>
#include <locale.h>
#include <stdio.h>
#include <string.h>

static unsigned int failures;

static void
text(const char *name, const char *value)
{
	printf("%s=%s\n", name, value == NULL ? "<NULL>" : value);
	if (value == NULL)
		failures++;
}

static void
error_result(const char *name, GError **error)
{
	if (*error == NULL) {
		printf("%s.error=<NULL>\n", name);
		failures++;
		return;
	}
	printf("%s.domain=%s code=%d message=%s\n", name,
	    g_quark_to_string((*error)->domain), (*error)->code,
	    (*error)->message == NULL ? "<NULL>" : (*error)->message);
	if ((*error)->message == NULL)
		failures++;
	g_clear_error(error);
}

static void
iconv_probe(const char *source)
{
	iconv_t converter;
	int saved;

	errno = 0;
	converter = iconv_open("UTF-8", source);
	saved = errno;
	printf("libc.iconv.%s=%s errno=%d\n", source,
	    converter == (iconv_t)-1 ? "FAIL" : "OK", saved);
	if (converter == (iconv_t)-1)
		failures++;
	else
		(void)iconv_close(converter);
}

int
main(void)
{
	GCancellable *cancel;
	GError *error = NULL;
	GSocket *socket;
	GInetAddress *address;
	GSocketAddress *endpoint;
	const char *charset = NULL;
	char message[256], byte;
	gchar *converted;
	gboolean result;
	gssize received;
	int code;

	(void)setvbuf(stdout, NULL, _IONBF, 0);
	text("locale", setlocale(LC_ALL, ""));
	text("libc.codeset", nl_langinfo(CODESET));
	result = g_get_charset(&charset);
	printf("glib.charset.utf8=%d\n", result);
	text("glib.charset.name", charset);
	text("libc.strerror.ECANCELED", strerror(ECANCELED));
	code = strerror_r(ECANCELED, message, sizeof(message));
	printf("libc.strerror_r.ECANCELED.ret=%d\n", code);
	if (code == 0)
		text("libc.strerror_r.ECANCELED.message", message);
	else
		failures++;
	iconv_probe("646");
	iconv_probe("US-ASCII");
	converted = g_convert("ASCII", -1, "UTF-8", "646", NULL, NULL, &error);
	text("glib.convert646", converted);
	g_free(converted);
	if (error != NULL)
		error_result("glib.convert646", &error);
	text("glib.strerror.ECANCELED", g_strerror(ECANCELED));
	text("glib.strerror.EAGAIN", g_strerror(EAGAIN));
	text("glib.gettext.glib20", g_dgettext("glib20", "Operation was cancelled"));
	g_set_error_literal(&error, G_IO_ERROR, G_IO_ERROR_CANCELLED,
	    "literal ASCII control");
	error_result("literal", &error);
	cancel = g_cancellable_new();
	g_cancellable_cancel(cancel);
	result = g_cancellable_set_error_if_cancelled(cancel, &error);
	printf("cancel.return=%d\n", result);
	if (!result)
		failures++;
	error_result("cancel", &error);
	socket = g_socket_new(G_SOCKET_FAMILY_IPV4, G_SOCKET_TYPE_DATAGRAM,
	    G_SOCKET_PROTOCOL_UDP, &error);
	if (socket == NULL) {
		error_result("socket.new", &error);
		failures++;
		goto done;
	}
	address = g_inet_address_new_from_string("127.0.0.1");
	endpoint = g_inet_socket_address_new(address, 0);
	g_object_unref(address);
	result = g_socket_bind(socket, endpoint, FALSE, &error);
	g_object_unref(endpoint);
	if (!result) {
		error_result("socket.bind", &error);
		failures++;
		goto socket_done;
	}
	g_socket_set_blocking(socket, FALSE);
	received = g_socket_receive(socket, &byte, 1, NULL, &error);
	printf("empty.socket.receive=%ld\n", (long)received);
	error_result("empty.socket", &error);
	result = g_socket_condition_timed_wait(socket, G_IO_IN, 1000, cancel,
	    &error);
	printf("cancel.socket.wait=%d\n", result);
	error_result("cancel.socket.wait", &error);
socket_done:
	g_object_unref(socket);
done:
	g_object_unref(cancel);
	printf("failures=%u\n", failures);
	return failures == 0 ? 0 : 1;
}
