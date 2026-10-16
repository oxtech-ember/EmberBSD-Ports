/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted), host fixtures for extracted ConsoleKit code.
 * The D-Bus credential transport is controlled here. GLib values are real.
 */
#include <gio/gio.h>
#include <assert.h>
#include <sys/types.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { CK_SESSION_ERROR_NOT_SUPPORTED = 1, CK_SESSION_ERROR_GENERAL,
       CK_SESSION_ERROR_INSUFFICIENT_PERMISSION, CK_SESSION_ERROR_FAILED };
typedef struct {
    GDBusProxy *bus_proxy;
    gchar *session_controller;
} Private;
typedef struct { Private *priv; uid_t owner; } CkSession;
typedef CkSession ConsoleKitSession;
typedef struct { dev_t tty; } CkProcessStat;
#define CK_SESSION(p) (p)
#define CK_IS_SESSION(p) ((p) != NULL)
#define CONSOLE_KIT_SESSION(p) (p)
#define NODEV ((dev_t)-1)
#define _(s) (s)
#define TRACE() ((void)0)

static uid_t caller_uid;
static gboolean backend, sender_present;
static int credential_failure, mutations, completed, thrown;
static const char *kernel_name;
static int failures, cases;

static GVariant *
credential_call(GDBusProxy *proxy, const gchar *method, GVariant *args,
                GDBusCallFlags flags, gint timeout, GCancellable *cancel,
                GError **error)
{
    (void)proxy; (void)flags; (void)timeout; (void)cancel;
    g_variant_ref_sink(args);
    g_variant_unref(args);
    gboolean uid_query = strcmp(method, "GetConnectionUnixUser") == 0;
    if ((uid_query && credential_failure == 1) ||
        (!uid_query && credential_failure == 2)) {
        g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_PERMISSION_DENIED,
                            "controlled credential lookup failure");
        assert(*error != NULL);
        return NULL;
    }
    g_assert(uid_query || strcmp(method, "GetConnectionUnixProcessID") == 0);
    GVariant *value = g_variant_ref_sink(g_variant_new("(u)", uid_query ? caller_uid : 987U));
    assert(value != NULL);
    return value;
}
#define g_dbus_proxy_call_sync credential_call

static const gchar *invocation_sender(GDBusMethodInvocation *invocation)
{ (void)invocation; return sender_present ? ":fixture.1" : NULL; }
#define g_dbus_method_invocation_get_sender invocation_sender
static gboolean ck_device_is_server_managed(void) { return backend; }
#define console_kit_session_get_unix_user(s) ((s)->owner)
static void throw_error(GDBusMethodInvocation *i, int code, const char *message)
{ (void)i; (void)message; thrown = code; }
static void ck_session_set_session_controller(CkSession *s, const char *name)
{ ++mutations; g_free(s->priv->session_controller); s->priv->session_controller = g_strdup(name); }
static void console_kit_session_complete_take_control(ConsoleKitSession *s,
                                                     GDBusMethodInvocation *i)
{ (void)s; (void)i; ++completed; }
static const char *fixture_devname(dev_t dev, mode_t mode)
{ (void)dev; (void)mode; return kernel_name; }
#define devname fixture_devname
#ifndef S_IFCHR
#define S_IFCHR 0020000
#endif

#include "extracted.c"

static void check(gboolean condition, const char *name)
{
    ++cases;
    if (!condition) { ++failures; fprintf(stderr, "FAIL: %s\n", name); }
}

static void control_case(const char *name, uid_t uid, gboolean force,
                         const char *existing, int failure, gboolean sender,
                         gboolean managed, int error, int change, int success)
{
    Private priv = { NULL, g_strdup(existing) };
    CkSession session = { &priv, 43210 };
    caller_uid = uid; backend = managed; sender_present = sender;
    credential_failure = failure;
    mutations = completed = thrown = 0;
    gboolean result = dbus_take_control(&session, NULL, force);
    check(result && thrown == error && mutations == change && completed == success &&
          ((!change && g_strcmp0(priv.session_controller, existing) == 0) ||
           (change && g_strcmp0(priv.session_controller, ":fixture.1") == 0)), name);
    g_free(priv.session_controller);
}

static void tty_case(const char *name, const char *input, gboolean ok, guint value)
{
    guint output = 101;
    gboolean result = ck_get_console_num_from_device(input, &output);
    check(result == ok && output == (ok ? value : 101), name);
}

int main(void)
{
    control_case("owner acquires", 43210, FALSE, NULL, 0, TRUE, TRUE, 0, 1, 1);
    control_case("root acquires", 0, FALSE, NULL, 0, TRUE, TRUE, 0, 1, 1);
    control_case("foreign UID cannot acquire", 43211, FALSE, NULL, 0, TRUE, TRUE,
                 CK_SESSION_ERROR_INSUFFICIENT_PERMISSION, 0, 0);
    control_case("foreign UID cannot force", 43211, TRUE, ":old", 0, TRUE, TRUE,
                 CK_SESSION_ERROR_INSUFFICIENT_PERMISSION, 0, 0);
    control_case("foreign UID cannot reuse sender", 43211, FALSE, ":fixture.1", 0, TRUE, TRUE,
                 CK_SESSION_ERROR_INSUFFICIENT_PERMISSION, 0, 0);
    control_case("owner cannot force another controller", 43210, TRUE, ":old", 0, TRUE, TRUE,
                 CK_SESSION_ERROR_INSUFFICIENT_PERMISSION, 0, 0);
    control_case("root force replaces", 0, TRUE, ":old", 0, TRUE, TRUE, 0, 1, 1);
    control_case("root without force preserves controller", 0, FALSE, ":old", 0, TRUE, TRUE,
                 CK_SESSION_ERROR_FAILED, 0, 0);
    control_case("owner idempotent", 43210, FALSE, ":fixture.1", 0, TRUE, TRUE, 0, 0, 1);
    control_case("UID lookup failure", 43210, FALSE, ":old", 1, TRUE, TRUE,
                 CK_SESSION_ERROR_GENERAL, 0, 0);
    control_case("PID lookup failure", 0, TRUE, ":old", 2, TRUE, TRUE,
                 CK_SESSION_ERROR_GENERAL, 0, 0);
    control_case("missing sender", 0, TRUE, ":old", 0, FALSE, TRUE,
                 CK_SESSION_ERROR_GENERAL, 0, 0);
    control_case("none backend still fails", 0, TRUE, ":old", 0, TRUE, FALSE,
                 CK_SESSION_ERROR_NOT_SUPPORTED, 0, 0);

    CkProcessStat stat = { 1 };
    kernel_name = "ttyE4";
    char *device = ck_process_stat_get_tty(&stat);
    check(g_strcmp0(device, "/dev/ttyE4") == 0, "normalize real NetBSD ttyE4");
    tty_case("normalized ttyE4 is VT5", device, TRUE, 5);
    g_free(device);
    const char *others[] = { "tty00", "pts/0", "ttyU0" };
    for (size_t i = 0; i < G_N_ELEMENTS(others); ++i) {
        kernel_name = others[i];
        device = ck_process_stat_get_tty(&stat);
        char *expected = g_strconcat("/dev/", others[i], NULL);
        check(g_strcmp0(device, expected) == 0, "preserve valid other kernel TTY");
        tty_case("other TTY is not a console", device, FALSE, 0);
        g_free(expected); g_free(device);
    }
    const char *bad_names[] = { NULL, "", "/dev/ttyE4", "/tmp/ttyE4", "../ttyE4",
                               "pts/../ttyE4", "./ttyE4", "pts/./0", "pts//0", "pts/" };
    for (size_t i = 0; i < G_N_ELEMENTS(bad_names); ++i) {
        kernel_name = bad_names[i];
        device = ck_process_stat_get_tty(&stat);
        check(device == NULL, "reject synthetic invalid kernel devname");
        g_free(device);
    }
    stat.tty = NODEV; kernel_name = "ttyE4";
    device = ck_process_stat_get_tty(&stat);
    check(device == NULL, "NODEV has no TTY"); g_free(device);
    tty_case("first console", "/dev/ttyE0", TRUE, 1);
    tty_case("multiple decimal digits", "/dev/ttyE12", TRUE, 13);
    tty_case("largest representable VT", "/dev/ttyE4294967294", TRUE, 4294967295U);
    const char *invalid[] = { NULL, "", "ttyE4", "/tmp/ttyE4", "/dev/tty00", "/dev/pts/0",
                             "/dev/ttyE", "/dev/ttyE04", "/dev/ttyE+4", "/dev/ttyE-1",
                             "/dev/ttyE 4", "/dev/ttyE4x", "/dev/ttyE4/", "/dev/ttyE4\n",
                             "/dev/ttyE4294967295", "/dev/ttyE4294967296",
                             "/dev/ttyE99999999999999999999999999999999999" };
    for (size_t i = 0; i < G_N_ELEMENTS(invalid); ++i)
        tty_case("reject malformed/nonconsole/overflow without output mutation", invalid[i], FALSE, 0);
    check(ck_get_console_num_from_device("/dev/ttyE4", NULL), "optional output pointer");
    printf("%d cases, %d failures\n", cases, failures);
    return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
