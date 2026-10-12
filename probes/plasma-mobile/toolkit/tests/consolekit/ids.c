/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Exercise installed Polkit against CK2 IDs. */
#include <polkit/polkit.h>
#include <unistd.h>

#define CK "org.freedesktop.ConsoleKit"
#define MANAGER "/org/freedesktop/ConsoleKit/Manager"
#define SESSION "/org/freedesktop/ConsoleKit/Session1"

static GMainLoop *loop;
static int failed;
static const char xml[] =
    "<node><interface name='" CK ".Manager'>"
    "<method name='GetSessionForUnixProcess'><arg type='u' direction='in'/>"
    "<arg type='o' direction='out'/></method></interface>"
    "<interface name='" CK ".Session'><method name='GetUser'>"
    "<arg type='u' direction='out'/></method></interface></node>";

static void
method(GDBusConnection *connection, const gchar *sender, const gchar *path,
    const gchar *iface, const gchar *name, GVariant *args,
    GDBusMethodInvocation *call, gpointer data)
{
    (void)connection; (void)sender; (void)iface; (void)data;
    if (g_str_equal(name, "GetSessionForUnixProcess")) {
        guint32 pid;
        g_variant_get(args, "(u)", &pid);
        if (pid != (guint32)getpid()) {
            g_dbus_method_invocation_return_dbus_error(call,
                CK ".Manager.Error.General", "No session for this process");
            return;
        }
        g_dbus_method_invocation_return_value(call, g_variant_new("(o)", SESSION));
    } else if (g_str_equal(name, "GetUser") && g_str_equal(path, SESSION)) {
        g_dbus_method_invocation_return_value(call, g_variant_new("(u)", (guint32)getuid()));
    } else {
        g_dbus_method_invocation_return_dbus_error(call,
            CK ".Session.Error.General", "Unexpected request");
    }
}

static gpointer
check(gpointer unused)
{
    GError *error = NULL;
    PolkitSubject *subject = NULL;
    (void)unused;
    subject = polkit_unix_session_new_for_process_sync(getpid(), NULL, &error);
    if (error || !subject || g_strcmp0(polkit_unix_session_get_session_id(
        POLKIT_UNIX_SESSION(subject)), "Session1") != 0) {
        g_printerr("FAIL: process lookup must return CK2 database ID Session1\n");
        failed = 1;
        goto out;
    }
    g_print("PASS: process lookup returns database ID\n");
    if (!polkit_subject_exists_sync(subject, NULL, &error) || error) {
        g_printerr("FAIL: resolve short ID to session object\n");
        failed = 1;
        goto out;
    }
    g_print("PASS: short ID resolves to session object\n");
    g_clear_object(&subject);
    subject = polkit_unix_session_new(SESSION);
    if (!polkit_subject_exists_sync(subject, NULL, &error) || error) {
        g_printerr("FAIL: existing full object path compatibility\n");
        failed = 1;
        goto out;
    }
    g_print("PASS: full object path remains supported\n");
    g_clear_object(&subject);
    subject = polkit_unix_session_new("SessionMissing");
    if (polkit_subject_exists_sync(subject, NULL, &error) || !error) {
        g_printerr("FAIL: absent session accepted\n");
        failed = 1;
        goto out;
    }
    g_clear_error(&error);
    g_clear_object(&subject);
    subject = polkit_unix_session_new_for_process_sync(0, NULL, &error);
    if (subject || !error) {
        g_printerr("FAIL: process without session accepted\n");
        failed = 1;
        goto out;
    }
    g_print("PASS: absent session and process return errors\n");
out:
    if (error)
        g_printerr("Detail: %s\n", error->message);
    g_clear_error(&error);
    g_clear_object(&subject);
    g_main_loop_quit(loop);
    return NULL;
}

int
main(int argc, char **argv)
{
    GTestDBus *bus;
    GDBusConnection *connection;
    GDBusNodeInfo *node;
    GVariant *reply;
    GThread *thread;
    GError *error = NULL;
    guint manager, session;
    static const GDBusInterfaceVTable vtable = { .method_call = method };

    g_test_init(&argc, &argv, NULL);
    bus = g_test_dbus_new(G_TEST_DBUS_NONE);
    g_test_dbus_up(bus);
    g_setenv("DBUS_SYSTEM_BUS_ADDRESS", g_test_dbus_get_bus_address(bus), TRUE);
    connection = g_bus_get_sync(G_BUS_TYPE_SYSTEM, NULL, &error);
    if (!connection)
        g_error("Private bus: %s", error->message);
    reply = g_dbus_connection_call_sync(connection, "org.freedesktop.DBus",
        "/org/freedesktop/DBus", "org.freedesktop.DBus", "RequestName",
        g_variant_new("(su)", CK, 0U), G_VARIANT_TYPE("(u)"),
        G_DBUS_CALL_FLAGS_NONE, 3000, NULL, &error);
    if (!reply)
        g_error("Private service name: %s", error->message);
    g_variant_unref(reply);
    node = g_dbus_node_info_new_for_xml(xml, &error);
    manager = g_dbus_connection_register_object(connection, MANAGER,
        node->interfaces[0], &vtable, NULL, NULL, &error);
    session = g_dbus_connection_register_object(connection, SESSION,
        node->interfaces[1], &vtable, NULL, NULL, &error);
    if (!manager || !session)
        g_error("Private objects: %s", error->message);
    loop = g_main_loop_new(NULL, FALSE);
    thread = g_thread_new("polkit-client", check, NULL);
    g_main_loop_run(loop);
    g_thread_join(thread);
    g_dbus_connection_unregister_object(connection, session);
    g_dbus_connection_unregister_object(connection, manager);
    g_dbus_connection_close_sync(connection, NULL, NULL);
    g_object_unref(connection);
    g_dbus_node_info_unref(node);
    g_main_loop_unref(loop);
    g_test_dbus_down(bus);
    g_object_unref(bus);
    return failed;
}
