/* SPDX-License-Identifier: BSD-2-Clause
 * Origin: EmberBSD (AI-assisted), actual GLib monitor and seat-consumer fixture.
 * Only console transport and generated session accessors are controlled.
 */
#include <glib.h>
#include <glib-object.h>
#include <glib/gstdio.h>
#include <glib/gi18n.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>

/* Platform selection applies to the included ConsoleKit source, not host headers. */
#define __NetBSD__ 1
#define VT_GETACTIVE 0x7856
#define VT_ACTIVATE 0x7857
#define ERROR -1
static int kernel_vt = 1, kernel_error, activation_error;
static guint requested_vt, ioctl_calls, getty_queries;
static int console_fd;
static int fixture_ioctl(int fd, unsigned long request, ...)
{
    g_assert(fd == console_fd);
    ++ioctl_calls;
    va_list ap;
    va_start(ap, request);
    if (request == VT_GETACTIVE) {
        int *value = va_arg(ap, int *);
        va_end(ap);
        if (kernel_error) { errno = kernel_error; return -1; }
        *value = kernel_vt;
    } else {
        g_assert(request == VT_ACTIVATE);
        requested_vt = va_arg(ap, guint);
        va_end(ap);
        if (!requested_vt || activation_error) { errno = EINVAL; return -1; }
    }
    return 0;
}
#define ioctl fixture_ioctl
#include "reader.c"
#undef ioctl

int ck_get_a_console_fd(void)
{ console_fd = open("/dev/null", O_RDONLY); return console_fd; }
gboolean ck_get_max_num_consoles(guint *num)
{ ++getty_queries; *num = 0; return TRUE; }
gboolean ck_wait_for_active_console_num(int fd, guint num)
{ (void)fd; (void)num; return FALSE; }

/* The complete upstream monitor runs with real GObject and GLib sources. */
#include "src/ck-vt-monitor.c"

typedef struct { gchar *id; const char *path; guint pause_devices_timer; } SessionPrivate;
typedef struct { GObject parent; SessionPrivate *priv; const char *device; gboolean active; } CkSession;
typedef struct { GObjectClass parent; } CkSessionClass;
typedef CkSession ConsoleKitSession;
static guint pauses, resumes;
G_DEFINE_TYPE(CkSession, fixture_session, G_TYPE_OBJECT)
static void fixture_session_finalize(GObject *object)
{
    CkSession *s = (CkSession *)object;
    g_free(s->priv);
    G_OBJECT_CLASS(fixture_session_parent_class)->finalize(object);
}
static void fixture_session_class_init(CkSessionClass *klass)
{ G_OBJECT_CLASS(klass)->finalize = fixture_session_finalize; }
static void fixture_session_init(CkSession *s)
{ s->priv = g_new0(SessionPrivate, 1); s->priv->path = "/fixture/session"; }
#define CK_IS_SESSION(s) ((s) != NULL)
#define CONSOLE_KIT_SESSION(s) (s)
static const char *console_kit_session_get_display_device(ConsoleKitSession *s) { return s->device; }
static const char *console_kit_session_get_x11_display_device(ConsoleKitSession *s) { (void)s; return NULL; }
static gboolean console_kit_session_get_active(ConsoleKitSession *s) { return s->active; }
static const char *ck_session_get_path(CkSession *s) { return s->priv->path; }
static void ck_session_pause_all_devices(CkSession *s, gboolean force)
{ g_assert(force); ++pauses; s->active = FALSE; }
static void ck_session_resume_all_devices(CkSession *s) { ++resumes; s->active = TRUE; }
static void ck_session_get_creation_time(CkSession *s, char **text, GError **error)
{ (void)s; (void)error; *text = g_strdup("2000-01-01T00:00:00Z"); }
/* The private test sessions need no diagnostic identifier; this is a valid NULL id. */
#include "session-consumer.c"

typedef struct { GHashTable *sessions; CkSession *active_session; } SeatPrivate;
typedef struct { GObject parent; SeatPrivate *priv; } CkSeat;
typedef struct { GObjectClass parent; } CkSeatClass;
static guint seat_signals[1];
G_DEFINE_TYPE(CkSeat, fixture_seat, G_TYPE_OBJECT)
static void fixture_seat_finalize(GObject *object)
{
    CkSeat *seat = (CkSeat *)object;
    g_clear_object(&seat->priv->active_session);
    g_hash_table_unref(seat->priv->sessions);
    g_free(seat->priv);
    G_OBJECT_CLASS(fixture_seat_parent_class)->finalize(object);
}
static void fixture_seat_class_init(CkSeatClass *klass)
{
    G_OBJECT_CLASS(klass)->finalize = fixture_seat_finalize;
    seat_signals[0] = g_signal_new("active-session-changed-full", G_TYPE_FROM_CLASS(klass),
                                  G_SIGNAL_RUN_LAST, 0, NULL, NULL, NULL,
                                  G_TYPE_NONE, 2, G_TYPE_POINTER, G_TYPE_POINTER);
}
static void fixture_seat_init(CkSeat *seat)
{
    seat->priv = g_new0(SeatPrivate, 1);
    seat->priv->sessions = g_hash_table_new(g_str_hash, g_str_equal);
}
#define CONSOLE_KIT_SEAT(s) (s)
static void console_kit_seat_emit_active_session_changed(CkSeat *s, const char *path)
{ (void)s; g_assert(path != NULL); }
#define signals seat_signals
#define ACTIVE_SESSION_CHANGED_FULL 0
#include "seat-consumer.c"
#undef signals

static guint emissions, last_vt;
static int cases, failures;
static void observe(CkVtMonitor *monitor, guint num, gpointer unused)
{ (void)monitor; (void)unused; ++emissions; last_vt = num; }
static void release_on_signal(CkVtMonitor *monitor, guint num, gpointer unused)
{ (void)num; (void)unused; g_object_unref(monitor); }
static void check(gboolean ok, const char *name)
{ ++cases; if (!ok) { ++failures; fprintf(stderr, "FAIL: %s\n", name); } }
static void dispatch_for(guint milliseconds)
{
    gint64 until = g_get_monotonic_time() + (gint64)milliseconds * 1000;
    while (g_get_monotonic_time() < until) {
        while (g_main_context_iteration(NULL, FALSE)) {}
        g_usleep(1000);
    }
    while (g_main_context_iteration(NULL, FALSE)) {}
}
static void reader_failure(int error, int value, const char *name)
{
    guint out = 77;
    kernel_error = error; kernel_vt = value;
    check(!ck_get_active_console_num(console_fd, &out) && out == 77, name);
}

int main(void)
{
    CkVtMonitor *monitor = ck_vt_monitor_new();
    int saved_fd = console_fd;
    CkSeat *seat = g_object_new(fixture_seat_get_type(), NULL);
    CkSession *first = g_object_new(fixture_session_get_type(), NULL);
    CkSession *second = g_object_new(fixture_session_get_type(), NULL);
    first->device = "/dev/ttyE0"; second->device = "/dev/ttyE4";
    g_hash_table_insert(seat->priv->sessions, "first", first);
    g_hash_table_insert(seat->priv->sessions, "second", second);
    g_signal_connect(monitor, "active-changed", G_CALLBACK(active_vt_changed), seat);
    g_signal_connect(monitor, "active-changed", G_CALLBACK(observe), NULL);
    update_active_vt(seat, 1);
    check(first->active && !second->active, "VT1 selects ttyE0");
    check(getty_queries == 0, "native watcher does not enumerate enabled gettys");
    kernel_vt = 5; dispatch_for(250);
    check(emissions == 1 && last_vt == 5 && second->active && !first->active,
          "sparse VT5 becomes active with zero enabled gettys");
    guint out = 77;
    kernel_vt = 42;
    check(ck_vt_monitor_get_active(monitor, &out, NULL) && out == 42,
          "get_active reads fresh high VT without a fixed maximum");
    dispatch_for(250);
    check(last_vt == 42 && seat->priv->active_session == NULL && !second->active,
          "new actual console without a session deactivates the old session");
    guint before = emissions;
    dispatch_for(250);
    check(emissions == before, "unchanged state emits no duplicate");
    requested_vt = 0; kernel_vt = 1;
    check(ck_vt_monitor_set_active(monitor, 42, NULL) && requested_vt == 42,
          "activation already-active check reads the kernel instead of stale cache");
    check(last_vt == 42, "request completion does not invent an active transition");
    kernel_vt = 5; dispatch_for(250);
    check(second->active && last_vt == 5, "only committed actual state activates session");
    before = emissions;
    GError *error = NULL;
    requested_vt = 0;
    check(!ck_vt_monitor_set_active(monitor, 5, &error) && error != NULL && requested_vt == 0,
          "already-active VT returns a real error");
    g_clear_error(&error);
    kernel_error = EIO; out = 77;
    check(!ck_vt_monitor_get_active(monitor, &out, &error) && error != NULL && out == 77,
          "get_active never returns cached success after ioctl failure");
    g_clear_error(&error);
    requested_vt = 0;
    check(!ck_vt_monitor_set_active(monitor, 1, &error) && error != NULL && requested_vt == 0,
          "failed query cannot issue activation");
    g_clear_error(&error);
    dispatch_for(250);
    check(last_vt == 0 && emissions == before + 1 && !first->active && !second->active &&
          seat->priv->active_session == NULL, "poll failure propagates through actual seat consumer to inactive");
    before = emissions; dispatch_for(250);
    check(emissions == before, "persistent failure does not emit duplicate inactive transitions");
    reader_failure(ENOTTY, 5, "ENOTTY preserves reader output");
    reader_failure(EINTR, 5, "EINTR preserves reader output");
    reader_failure(0, 0, "no active screen preserves reader output");
    reader_failure(0, -1, "negative active number preserves reader output");
    char *device = ck_get_console_device_for_num(0);
    check(device == NULL, "unknown VT cannot match an unsigned-underflow device path"); g_free(device);
    kernel_error = 0; kernel_vt = 1; dispatch_for(250);
    check(last_vt == 1 && first->active && !second->active, "poll recovers to actual ttyE0 session");
    activation_error = 1;
    check(!ck_vt_monitor_set_active(monitor, 5, &error) && error != NULL,
          "activation ioctl failure stays an error"); g_clear_error(&error);
    activation_error = 0;
    check(!ck_vt_monitor_set_active(monitor, 0, &error) && error != NULL,
          "invalid zero VT is rejected by the real activation wrapper"); g_clear_error(&error);
    before = emissions;
    gpointer weak = monitor;
    g_object_add_weak_pointer(G_OBJECT(monitor), &weak);
    g_object_unref(monitor);
    check(weak == NULL, "timer does not create a persistent reference cycle");
    check(fcntl(saved_fd, F_GETFD) == -1 && errno == EBADF, "finalize closes console fd");
    guint calls = ioctl_calls;
    kernel_vt = 5; dispatch_for(250);
    check(ioctl_calls == calls && emissions == before, "finalize removes timeout without a stale callback");
    monitor = ck_vt_monitor_new();
    weak = monitor; g_object_add_weak_pointer(G_OBJECT(monitor), &weak);
    g_signal_connect(monitor, "active-changed", G_CALLBACK(release_on_signal), NULL);
    kernel_vt = 1; dispatch_for(250);
    check(weak == NULL, "release of the last external owner during callback is safe");
    g_object_unref(seat); g_object_unref(first); g_object_unref(second);
    printf("%d cases, %d failures\n", cases, failures);
    return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
