/* SPDX-License-Identifier: BSD-2-Clause
 * Execute extracted CK methods with real generated GDBus replies and FD lists.
 * Device construction is controlled. This does not enable a device backend.
 */
#define _POSIX_C_SOURCE 200809L
#include <gio/gio.h>
#include <gio/gunixfdlist.h>
#include <fcntl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include "ck-session-generated.h"

typedef struct {
        GObject parent;
        int fd;
        guint major, minor;
        gboolean active;
} CkDevice;
typedef GObjectClass CkDeviceClass;
G_DEFINE_TYPE(CkDevice, fixture_device, G_TYPE_OBJECT)
static guint created, finalized;
static int next_fd = -2;
static gboolean exhaust_append;
static gboolean preseed_list;
static int next_active = -1;
static guint lists_created, lists_finalized;

static void fixture_device_finalize(GObject *object)
{
        CkDevice *device = (CkDevice *)object;
        if (device->fd >= 0)
                close(device->fd);
        finalized++;
        G_OBJECT_CLASS(fixture_device_parent_class)->finalize(object);
}
static void fixture_device_class_init(CkDeviceClass *klass)
{
        klass->finalize = fixture_device_finalize;
}
static void fixture_device_init(CkDevice *device) { device->fd = -1; }
static CkDevice *ck_device_new(guint major, guint minor, gboolean active)
{
        CkDevice *device = g_object_new(fixture_device_get_type(), NULL);
        device->active = next_active < 0 ? active : next_active;
        next_active = -1;
        device->major = major;
        device->minor = minor;
        device->fd = next_fd == -2 ? open("/dev/null", O_RDWR) : next_fd;
        next_fd = -2;
        created++;
        return device;
}
static gboolean ck_device_compare(CkDevice *d, guint major, guint minor)
{ return d->major == major && d->minor == minor; }
static int ck_device_get_fd(CkDevice *d) { return d->fd; }
#define DEVICE_EVDEV 1
#define CK_DEVICE(o) ((CkDevice *)(o))
#define CK_IS_DEVICE(o) (G_TYPE_CHECK_INSTANCE_TYPE((o), fixture_device_get_type()))
static int ck_device_get_category(CkDevice *d) { (void)d; return 0; }

typedef struct { char *session_controller; GList *devices; } SessionPrivate;
typedef struct { SessionPrivate *priv; ConsoleKitSession *object; } CkSession;
static CkSession session;
static gboolean ck_device_get_active(CkDevice *device)
{ return device->active; }
static CkSession *fixture_session(ConsoleKitSession *object)
{ g_assert(object == session.object); return &session; }
#define CK_SESSION(o) fixture_session(o)
#undef CONSOLE_KIT_SESSION
#define CONSOLE_KIT_SESSION(s) ((s)->object)
#define TRACE() ((void)0)
#define ck_session_print_list_size(s) ((void)(s))
#define _(s) (s)
#define CK_SESSION_ERROR_FAILED 1
#define CK_SESSION_ERROR_GENERAL 2
#define CK_SESSION_ERROR_NOT_SUPPORTED 3
static void throw_error(GDBusMethodInvocation *invocation, int code, const char *message)
{
        (void)code;
        g_dbus_method_invocation_return_dbus_error(invocation, "org.example.CK.Error", message);
}
static void list_finalized(gpointer data, GObject *object)
{ (void)data; (void)object; lists_finalized++; }
static GUnixFDList *track_list(GUnixFDList *list)
{
        lists_created++;
        g_object_weak_ref(G_OBJECT(list), list_finalized, NULL);
        return list;
}
static GUnixFDList *tracked_array(const int *fds, int count)
{ return track_list(g_unix_fd_list_new_from_array(fds, count)); }
static GUnixFDList *tracked_new(void)
{
        GUnixFDList *list = track_list(g_unix_fd_list_new());
        if (preseed_list) {
                GError *error = NULL;
                int fd = open("/dev/null", O_RDONLY);
                g_assert_cmpint(fd, >=, 0);
                g_assert_cmpint(g_unix_fd_list_append(list, fd, &error), ==, 0);
                g_assert_no_error(error);
                close(fd);
        }
        return list;
}
static int checked_append(GUnixFDList *list, int fd, GError **error)
{
        struct rlimit saved, limited;
        int result;
        if (!exhaust_append)
                return g_unix_fd_list_append(list, fd, error);
        exhaust_append = FALSE;
        g_assert_cmpint(getrlimit(RLIMIT_NOFILE, &saved), ==, 0);
        limited = saved;
        limited.rlim_cur = 0;
        g_assert_cmpint(setrlimit(RLIMIT_NOFILE, &limited), ==, 0);
        result = g_unix_fd_list_append(list, fd, error);
        g_assert_cmpint(setrlimit(RLIMIT_NOFILE, &saved), ==, 0);
        g_assert_cmpint(result, ==, -1);
        g_assert_error(*error, G_IO_ERROR, G_IO_ERROR_TOO_MANY_OPEN_FILES);
        return result;
}
static void ck_session_remove_device(CkSession *, CkDevice *);
#define g_unix_fd_list_new_from_array tracked_array
#define g_unix_fd_list_new tracked_new
#define g_unix_fd_list_append checked_append
#include "extracted.c"
#undef g_unix_fd_list_new_from_array
#undef g_unix_fd_list_new
#undef g_unix_fd_list_append

static GMainContext *context;
static GMainLoop *loop;
static GDBusConnection *server;
static char *address;
static GMutex lock;
static GCond condition;
static gboolean ready, done;
static void barrier(void (*action)(void));
static void cleanup_devices(void) { ck_session_remove_all_devices(&session); }
static gpointer serve(gpointer data)
{
        GError *error = NULL;
        (void)data;
        g_main_context_push_thread_default(context);
        server = g_dbus_connection_new_for_address_sync(address,
            G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT | G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,
            NULL, NULL, &error);
        g_assert_no_error(error);
        session.object = console_kit_session_skeleton_new();
        g_signal_connect(session.object, "handle-take-device", G_CALLBACK(dbus_take_device), NULL);
        g_signal_connect(session.object, "handle-release-device", G_CALLBACK(dbus_release_device), NULL);
        g_assert(g_dbus_interface_skeleton_export(G_DBUS_INTERFACE_SKELETON(session.object),
            server, "/org/example/Session", &error));
        g_assert_no_error(error);
        g_mutex_lock(&lock);
        ready = TRUE;
        g_cond_signal(&condition);
        g_mutex_unlock(&lock);
        g_main_loop_run(loop);
        cleanup_devices();
        g_dbus_interface_skeleton_unexport(G_DBUS_INTERFACE_SKELETON(session.object));
        g_clear_object(&session.object);
        g_dbus_connection_close_sync(server, NULL, &error);
        g_assert_no_error(error);
        g_clear_object(&server);
        g_main_context_pop_thread_default(context);
        return NULL;
}
static gboolean run_action(gpointer data)
{
        void (*action)(void) = data;
        if (action)
                action();
        g_mutex_lock(&lock);
        done = TRUE;
        g_cond_signal(&condition);
        g_mutex_unlock(&lock);
        return G_SOURCE_REMOVE;
}
static void barrier(void (*action)(void))
{
        g_mutex_lock(&lock);
        done = FALSE;
        g_main_context_invoke(context, run_action, action);
        while (!done)
                g_cond_wait(&condition, &lock);
        g_mutex_unlock(&lock);
}
static GVariant *call(GDBusConnection *client, const char *method, guint minor,
    GUnixFDList **fds, GError **error)
{
        GVariant *reply = g_dbus_connection_call_with_unix_fd_list_sync(client,
            g_dbus_connection_get_unique_name(server), "/org/example/Session",
            "org.freedesktop.ConsoleKit.Session", method, g_variant_new("(uu)", 1, minor),
            NULL, G_DBUS_CALL_FLAGS_NONE, 1000, NULL, fds, NULL, error);
        barrier(NULL);
        return reply;
}
static guint cases, failures;
#define CHECK(test, text) do { cases++; if (!(test)) { failures++; g_printerr("FAIL: %s\n", text); } } while (0)
static void active(void) { console_kit_session_set_active(session.object, TRUE); }
static void inactive(void) { console_kit_session_set_active(session.object, FALSE); }
static void stop(void) { g_main_loop_quit(loop); }
int main(void)
{
        SessionPrivate priv = {0};
        GDBusConnection *client, *foreign;
        GThread *thread;
        GError *error = NULL;
        GVariant *reply;
        GUnixFDList *fds = NULL;
        int canonical, received, handle, saved_stdin;
        gboolean paused;
        guint old_created, old_finalized;
        struct stat st;
        /* Observe upstream API functions even in a baseline that does not call them. */
        (void)tracked_array; (void)tracked_new; (void)checked_append; (void)ck_device_get_active;
        /* The runner owns a dedicated daemon. Never use the user's session bus. */
        g_assert(g_getenv("CK_TEST_BUS_ADDRESS"));
        address = g_strdup(g_getenv("CK_TEST_BUS_ADDRESS"));
        context = g_main_context_new();
        loop = g_main_loop_new(context, FALSE);
        session.priv = &priv;
        thread = g_thread_new("CK FD service", serve, NULL);
        g_mutex_lock(&lock);
        while (!ready)
                g_cond_wait(&condition, &lock);
        g_mutex_unlock(&lock);
        client = g_dbus_connection_new_for_address_sync(address,
            G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT | G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,
            NULL, NULL, &error);
        g_assert_no_error(error);
        priv.session_controller = g_strdup(g_dbus_connection_get_unique_name(client));
        barrier(active);
        reply = call(client, "TakeDevice", 1, &fds, &error);
        CHECK(reply && !error && fds, "real generated TakeDevice reply carries FD list");
        g_assert(reply && fds);
        g_variant_get(reply, "(hb)", &handle, &paused);
        CHECK(handle == 0 && !paused, "active device reports inactive=false");
        canonical = ((CkDevice *)priv.devices->data)->fd;
        received = g_unix_fd_list_get(fds, handle, &error);
        g_assert_no_error(error);
        CHECK(received >= 0 && fstat(received, &st) == 0, "received SCM_RIGHTS FD is usable");
        g_clear_pointer(&reply, g_variant_unref);
        g_clear_object(&fds);
        CHECK(fcntl(canonical, F_GETFD) >= 0, "reply teardown preserves canonical FD");
        CHECK(lists_created == lists_finalized, "local outgoing list reference is released");
        reply = call(client, "TakeDevice", 1, &fds, &error);
        CHECK(!reply && error && g_list_length(priv.devices) == 1, "duplicate TakeDevice fails without list mutation");
        g_clear_error(&error);
        reply = call(client, "ReleaseDevice", 1, &fds, &error);
        CHECK(reply && !error && !priv.devices, "ReleaseDevice removes tracked device");
        CHECK(fcntl(canonical, F_GETFD) < 0 && errno == EBADF, "ReleaseDevice closes canonical FD");
        CHECK(fstat(received, &st) == 0, "received duplicate survives canonical close");
        close(received);
        g_clear_pointer(&reply, g_variant_unref);
        barrier(inactive);
        reply = call(client, "TakeDevice", 2, &fds, &error);
        CHECK(reply && !error, "inactive fixture device can be exported");
        g_assert(reply);
        g_variant_get(reply, "(hb)", &handle, &paused);
        CHECK(paused, "inactive device reports inactive=true");
        g_clear_pointer(&reply, g_variant_unref);
        g_clear_object(&fds);
        barrier(cleanup_devices);
        barrier(active);
        next_active = FALSE;
        preseed_list = TRUE;
        reply = call(client, "TakeDevice", 7, &fds, &error);
        CHECK(reply && !error && fds, "preseeded real FD list can be exported");
        g_assert(reply && fds);
        g_variant_get(reply, "(hb)", &handle, &paused);
        CHECK(handle == 1, "reply uses actual append index, not a hardcoded zero");
        CHECK(paused, "inactive comes from actual device, not session active property");
        received = g_unix_fd_list_get(fds, handle, &error);
        g_assert_no_error(error);
        CHECK(fcntl(received, F_GETFL) >= 0 && (fcntl(received, F_GETFL) & O_ACCMODE) == O_RDWR,
            "handle selects requested FD instead of preseeded read-only FD");
        close(received);
        preseed_list = FALSE;
        g_clear_pointer(&reply, g_variant_unref); g_clear_object(&fds);
        barrier(cleanup_devices);
        next_fd = -1;
        old_created = created; old_finalized = finalized;
        reply = call(client, "TakeDevice", 3, &fds, &error);
        CHECK(!reply && error, "missing canonical FD sends error");
        CHECK(!priv.devices && created == old_created + 1 && finalized == old_finalized + 1,
            "missing FD rolls back newly-created device and reference");
        g_clear_error(&error);
        barrier(cleanup_devices);
        exhaust_append = TRUE;
        old_finalized = finalized;
        reply = call(client, "TakeDevice", 4, &fds, &error);
        CHECK(!reply && error, "real append EMFILE sends no success reply");
        CHECK(!priv.devices && finalized == old_finalized + 1, "append failure rolls back new device");
        exhaust_append = FALSE;
        g_clear_error(&error);
        g_clear_pointer(&reply, g_variant_unref);
        g_clear_object(&fds);
        barrier(cleanup_devices);
        foreign = g_dbus_connection_new_for_address_sync(address,
            G_DBUS_CONNECTION_FLAGS_AUTHENTICATION_CLIENT | G_DBUS_CONNECTION_FLAGS_MESSAGE_BUS_CONNECTION,
            NULL, NULL, &error);
        g_assert_no_error(error);
        old_created = created;
        reply = call(foreign, "TakeDevice", 5, &fds, &error);
        CHECK(!reply && error && !priv.devices && old_created == created, "foreign controller cannot construct or export a device");
        g_clear_error(&error);
        g_dbus_connection_close_sync(foreign, NULL, &error);
        g_assert_no_error(error);
        g_object_unref(foreign);
        /* FD zero is valid. Restore the fixture's stdin after the transaction. */
        saved_stdin = dup(STDIN_FILENO);
        canonical = open("/dev/null", O_RDWR);
        g_assert_cmpint(canonical, >=, 0);
        g_assert_cmpint(dup2(canonical, STDIN_FILENO), ==, STDIN_FILENO);
        close(canonical);
        next_fd = STDIN_FILENO;
        reply = call(client, "TakeDevice", 6, &fds, &error);
        CHECK(reply && !error && fds, "canonical FD zero is accepted");
        g_clear_pointer(&reply, g_variant_unref);
        g_clear_object(&fds);
        barrier(cleanup_devices);
        if (saved_stdin >= 0) { g_assert_cmpint(dup2(saved_stdin, STDIN_FILENO), ==, STDIN_FILENO); close(saved_stdin); }
        /* Exercise the real generated completion's NO_REPLY_EXPECTED branch. */
        {
                GDBusMessage *message = g_dbus_message_new_method_call(
                    g_dbus_connection_get_unique_name(server), "/org/example/Session",
                    "org.freedesktop.ConsoleKit.Session", "TakeDevice");
                g_dbus_message_set_body(message, g_variant_new("(uu)", 1, 8));
                g_dbus_message_set_flags(message, G_DBUS_MESSAGE_FLAGS_NO_REPLY_EXPECTED);
                g_assert(g_dbus_connection_send_message(client, message, G_DBUS_SEND_MESSAGE_FLAGS_NONE, NULL, &error));
                g_assert_no_error(error);
                g_object_unref(message);
                reply = call(client, "ReleaseDevice", 8, &fds, &error);
                CHECK(reply && !error && !priv.devices, "NO_REPLY_EXPECTED completion retains releasable canonical ownership");
                CHECK(lists_created == lists_finalized, "NO_REPLY_EXPECTED completion does not leak list");
                g_clear_pointer(&reply, g_variant_unref);
        }
        for (guint i = 0; i < 20; i++) {
                reply = call(client, "TakeDevice", 100 + i, &fds, &error);
                CHECK(reply && !error, "repeated TakeDevice succeeds");
                g_clear_pointer(&reply, g_variant_unref); g_clear_object(&fds);
                reply = call(client, "ReleaseDevice", 100 + i, &fds, &error);
                CHECK(reply && !error && !priv.devices, "repeated ReleaseDevice balances entry");
                g_clear_pointer(&reply, g_variant_unref);
        }
        CHECK(created == finalized, "every constructed device reference is released");
        CHECK(lists_created == lists_finalized, "repeated cycles finalize every outgoing list");
        barrier(stop);
        g_thread_join(thread);
        g_dbus_connection_close_sync(client, NULL, &error);
        g_assert_no_error(error);
        g_object_unref(client);
        g_main_loop_unref(loop); g_main_context_unref(context);
        g_free(priv.session_controller); g_free(address);
        g_print("%u cases, %u failures\n", cases, failures);
        return failures ? 1 : 0;
}
