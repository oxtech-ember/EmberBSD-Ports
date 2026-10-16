/* SPDX-License-Identifier: BSD-2-Clause
 * Test the shipped D-Bus method policy with real nonroot Unix credentials.
 */
#include <gio/gio.h>
#include <unistd.h>
static GMainContext *context;
static GMainLoop *loop;
static GDBusConnection *service;
static GMutex mutex;
static GCond cond;
static gboolean ready;
static void method(GDBusConnection *c, const gchar *sender, const gchar *path,
    const gchar *iface, const gchar *name, GVariant *args,
    GDBusMethodInvocation *invocation, gpointer data)
{
        (void)c; (void)sender; (void)path; (void)iface; (void)name; (void)args; (void)data;
        g_dbus_method_invocation_return_value(invocation, g_variant_new("(s)", "policy-reached-handler"));
}
static gpointer serve(gpointer data)
{
        const GDBusInterfaceVTable vtable = { .method_call = method };
        GDBusNodeInfo *info;
        GVariant *reply;
        GError *error = NULL;
        guint registration;
        (void)data;
        g_main_context_push_thread_default(context);
        service = g_dbus_connection_new_for_address_sync(g_getenv("CK_TEST_BUS_ADDRESS"),
            G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT | G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,
            NULL, NULL, &error);
        g_assert_no_error(error);
        reply = g_dbus_connection_call_sync(service, "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "RequestName", g_variant_new("(su)", "org.freedesktop.ConsoleKit", 0),
            NULL, G_DBUS_CALL_FLAGS_NONE, 1000, NULL, &error);
        g_assert_no_error(error); g_assert_nonnull(reply); g_variant_unref(reply);
        info = g_dbus_node_info_new_for_xml("<node><interface name='org.freedesktop.ConsoleKit.Manager'>"
            "<method name='OpenSession'><arg type='s' direction='out'/></method>"
            "<method name='OpenSessionWithParameters'><arg type='a(sv)' direction='in'/><arg type='s' direction='out'/></method>"
            "</interface></node>", &error);
        g_assert_no_error(error);
        registration = g_dbus_connection_register_object(service, "/org/freedesktop/ConsoleKit/Manager",
            info->interfaces[0], &vtable, NULL, NULL, &error);
        g_assert_no_error(error); g_assert_cmpuint(registration, >, 0);
        g_mutex_lock(&mutex); ready = TRUE; g_cond_signal(&cond); g_mutex_unlock(&mutex);
        g_main_loop_run(loop);
        g_dbus_connection_unregister_object(service, registration);
        g_dbus_node_info_unref(info);
        g_dbus_connection_close_sync(service, NULL, &error); g_assert_no_error(error);
        g_object_unref(service);
        g_main_context_pop_thread_default(context);
        return NULL;
}
int main(void)
{
        GDBusConnection *client;
        GThread *thread;
        GError *error = NULL;
        GVariant *reply, *params;
        gboolean denied, ordinary;
        g_assert_cmpuint(geteuid(), !=, 0);
        context = g_main_context_new(); loop = g_main_loop_new(context, FALSE);
        thread = g_thread_new("policy service", serve, NULL);
        g_mutex_lock(&mutex); while (!ready) g_cond_wait(&cond, &mutex); g_mutex_unlock(&mutex);
        client = g_dbus_connection_new_for_address_sync(g_getenv("CK_TEST_BUS_ADDRESS"),
            G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT | G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,
            NULL, NULL, &error);
        g_assert_no_error(error);
        params = g_variant_new_array(G_VARIANT_TYPE("(sv)"), NULL, 0);
        reply = g_dbus_connection_call_sync(client, "org.freedesktop.ConsoleKit", "/org/freedesktop/ConsoleKit/Manager",
            "org.freedesktop.ConsoleKit.Manager", "OpenSessionWithParameters", g_variant_new("(@a(sv))", params),
            NULL, G_DBUS_CALL_FLAGS_NONE, 1000, NULL, &error);
        denied = !reply && g_error_matches(error, G_DBUS_ERROR, G_DBUS_ERROR_ACCESS_DENIED);
        g_clear_error(&error); g_clear_pointer(&reply, g_variant_unref);
        reply = g_dbus_connection_call_sync(client, "org.freedesktop.ConsoleKit", "/org/freedesktop/ConsoleKit/Manager",
            "org.freedesktop.ConsoleKit.Manager", "OpenSession", g_variant_new("()"),
            NULL, G_DBUS_CALL_FLAGS_NONE, 1000, NULL, &error);
        ordinary = reply && !error;
        g_clear_error(&error); g_clear_pointer(&reply, g_variant_unref);
        g_main_loop_quit(loop); g_thread_join(thread);
        g_dbus_connection_close_sync(client, NULL, &error); g_assert_no_error(error); g_object_unref(client);
        g_main_loop_unref(loop); g_main_context_unref(context);
        g_print("default policy: privileged denied=%d, ordinary allowed=%d\n", denied, ordinary);
        return denied && ordinary ? 0 : 1;
}
