/* SPDX-License-Identifier: BSD-2-Clause
 * Execute actual manager credential lookup and registration entry points.
 */
#include <gio/gio.h>
#include <sys/types.h>
#include <stdarg.h>
#include <assert.h>
typedef struct { GDBusProxy *bus_proxy; } Private;
typedef struct { Private *priv; } CkManager;
typedef CkManager ConsoleKitManager;
#define CK_MANAGER(o) (o)
#define TRACE() ((void)0)
#define _(s) (s)
#define CK_MANAGER_ERROR_GENERAL 1
#define CK_MANAGER_ERROR_INSUFFICIENT_PERMISSION 2
static guint uid_value, pid_value, queries, creations, errors;
static int fail_query, error_code;
static const char *sender = ":1.7";
static GVariant *expected_parameters;
static const gchar *invocation_sender(GDBusMethodInvocation *invocation)
{ (void)invocation; return sender; }
static GVariant *credential_query(GDBusProxy *proxy, const gchar *method,
    GVariant *parameters, GDBusCallFlags flags, gint timeout,
    GCancellable *cancel, GError **error)
{
        GVariant *value;
        (void)proxy; (void)flags; (void)timeout; (void)cancel;
        g_assert_nonnull(parameters);
        g_variant_ref_sink(parameters); g_variant_unref(parameters);
        queries++;
        if (fail_query == (int)queries) {
                g_set_error_literal(error, G_IO_ERROR, G_IO_ERROR_CLOSED, "controlled credential lookup failure");
                assert(*error != NULL);
                return NULL;
        }
        value = g_variant_ref_sink(g_variant_new("(u)",
            g_str_equal(method, "GetConnectionUnixUser") ? uid_value : pid_value));
        assert(value != NULL);
        return value;
}
static gboolean create_session_for_sender(CkManager *manager, const char *name,
    const GVariant *parameters, GDBusMethodInvocation *invocation)
{
        (void)manager; (void)invocation;
        g_assert(name == sender);
        g_assert(parameters == expected_parameters);
        creations++;
        return TRUE;
}
static void throw_error(GDBusMethodInvocation *invocation, int code, const char *format, ...)
{ (void)invocation; (void)format; errors++; error_code = code; }
#define g_dbus_proxy_call_sync credential_query
#define g_dbus_method_invocation_get_sender invocation_sender
#include "manager-extracted.c"
#undef g_dbus_proxy_call_sync
#undef g_dbus_method_invocation_get_sender
static guint cases, failures;
#define CHECK(test, text) do { cases++; if (!(test)) { failures++; g_printerr("FAIL: %s\n", text); } } while (0)
int main(void)
{
        Private priv = { (GDBusProxy *)&priv };
        CkManager manager = { &priv };
        GDBusMethodInvocation *invocation = (GDBusMethodInvocation *)&manager;
        GVariant *params = g_variant_ref_sink(g_variant_new_parsed(
            "[('unix-user', <uint32 0>), ('is-local', <true>),"
            " ('vtnr', <uint32 5>), ('display-device', <'/dev/ttyE4'>)]"));
        const guint users[] = { 0, 501, 65534 };
        (void)get_caller_info;
        (void)throw_error;
        expected_parameters = params;
        pid_value = 1234;
        for (guint i = 0; i < G_N_ELEMENTS(users); i++) {
                for (int failure = 0; failure < 3; failure++) {
                        queries = creations = errors = 0;
                        uid_value = users[i]; fail_query = failure;
                        dbus_open_session_with_parameters(&manager, invocation, params);
                        CHECK(creations == (users[i] == 0 && failure == 0 ? 1u : 0u), "only fully verified root may create a parameterized session");
                        CHECK(errors == (users[i] == 0 && failure == 0 ? 0u : 1u), "rejected credential paths send one error");
                        CHECK(queries == (failure == 1 ? 1u : 2u), "both credential lookups precede authorization");
                        if (users[i] != 0 || failure != 0)
                                CHECK(error_code == (failure ? CK_MANAGER_ERROR_GENERAL : CK_MANAGER_ERROR_INSUFFICIENT_PERMISSION), "credential failure and nonroot errors stay distinct");
                }
        }
        for (int missing = 0; missing < 2; missing++) {
                queries = creations = errors = 0; fail_query = 0;
                if (missing == 0) sender = NULL; else priv.bus_proxy = NULL;
                dbus_open_session_with_parameters(&manager, invocation, params);
                CHECK(creations == 0 && errors == 1 && queries == 0, "missing sender or credential proxy cannot create a leader");
                sender = ":1.7"; priv.bus_proxy = (GDBusProxy *)&priv;
        }
        expected_parameters = NULL;
        queries = creations = errors = 0;
        dbus_open_session(&manager, invocation);
        CHECK(creations == 1 && errors == 0 && queries == 0, "ordinary OpenSession keeps its existing creation path");
        g_variant_unref(params);
        g_print("%u manager cases, %u failures\n", cases, failures);
        return failures ? 1 : 0;
}
