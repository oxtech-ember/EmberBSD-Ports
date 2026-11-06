// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <glib-object.h>
#include <cassert>
#include <cstdio>
#include <functional>
#include <stdexcept>
#define __WXGTK4__ 1
#define wxUSE_EXCEPTIONS 1
#define wxUSE_THREADS 0
#define wxDEBUG_LEVEL 0
#define wxEVT_CATEGORY_ALL 0xffff
#define wxT(x) x
#define wxCHECK_RET(c, msg) do { if (!(c)) throw std::runtime_error(msg); } while (0)
#define wxCHECK_MSG(c, ret, msg) wxCHECK_RET(c, msg)
#define wxLogWarning(msg) ((void)(msg))
struct ScopeExit { std::function<void()> fn; ~ScopeExit() { fn(); } };
#define wxON_BLOCK_EXIT1(fn, value) auto savedValue = value; ScopeExit unref{[savedValue] { fn(savedValue); }}
#define wxON_BLOCK_EXIT_SET(ref, value) ScopeExit reset{[&] { ref = value; }}
struct wxApp
{
    bool fail = false;
    int wakeups = 0;
    unsigned m_idleSourceId = 0;
    int idles = 0;
    bool pending = false, active = false;
    std::function<void()> idleFn;
    bool EventsPending();
    void WakeUpIdle();
    bool DoIdle();
    void ProcessPendingEvents() { pending = false; }
    bool ProcessIdle() { ++idles; if (idleFn) idleFn(); return false; }
    bool HasPendingEvents() { return pending; }
    void SetActive(bool value, void*) { active = value; }
    void RethrowStoredException() { if (fail) throw std::runtime_error("stored"); }
};
static wxApp* wxTheApp;
static guint gs_idleSignals[2];
static gulong gs_idleHooks[2];
static unsigned gs_focusChange;
static GType surfaceType;
#define GDK_TYPE_SURFACE surfaceType
// PRODUCTION_IDLE_METHODS
class wxEventLoopBase
{
public:
    bool m_shouldExit = false, running = false;
    int exits = 0, yields = 0;
    virtual ~wxEventLoopBase() {}
    bool IsInsideRun() const { return running; }
    bool IsRunning() const { return running; }
    void OnExit() { ++exits; }
    virtual bool YieldFor(long events) { DoYieldFor(events); return true; }
    virtual void DoYieldFor(long) { ++yields; }
};
class wxGUIEventLoop : public wxEventLoopBase
{
public:
    wxGUIEventLoop();
    int m_exitcode;
    GMainLoop* m_loop;
    int DoRun();
    void ScheduleExit(int rc = 0);
    void WakeUp();
    bool Pending() const;
    bool Dispatch();
    int DispatchTimeout(unsigned long timeout);
    bool YieldFor(long events) override;
    void DoYieldFor(long events) override;
    int Run() {
        m_shouldExit = false; running = true;
        ScopeExit reset{[&] { running = false; }};
        return DoRun();
    }
};
// PRODUCTION_LOOP_METHODS

struct Nested
{
    wxGUIEventLoop outer, inner;
    bool outerRequested = false, innerFinished = false;
};
static gboolean StartNested(gpointer p)
{
    Nested* n = static_cast<Nested*>(p);
    g_timeout_add(2, [](gpointer p) -> gboolean {
        Nested* n = static_cast<Nested*>(p);
        n->outer.ScheduleExit(17);
        n->outerRequested = true;
        assert(!n->innerFinished);
        return FALSE;
    }, n);
    g_timeout_add(5, [](gpointer p) -> gboolean {
        Nested* n = static_cast<Nested*>(p);
        assert(n->outerRequested && !n->inner.m_shouldExit);
        n->inner.ScheduleExit(23);
        return FALSE;
    }, n);
    assert(n->inner.Run() == 23);
    n->innerFinished = true;
    return FALSE;
}
static gboolean QuitLoop(gpointer p)
{
    static_cast<wxGUIEventLoop*>(p)->ScheduleExit(31);
    return FALSE;
}
int main()
{
    Nested n;
    g_idle_add(StartNested, &n);
    assert(n.outer.Run() == 17 && n.innerFinished);
    assert(n.outer.exits == 1 && n.inner.exits == 1);
    assert(!n.outer.m_loop && !n.inner.m_loop);
    std::puts("nested outer/inner exit ordering PASS");

    g_idle_add(QuitLoop, &n.outer);
    assert(n.outer.Run() == 31 && n.outer.exits == 2);
    std::puts("same loop restart PASS");

    wxGUIEventLoop loop;
    loop.running = true;
    loop.ScheduleExit(41); // exit requested by OnEventLoopEnter, before DoRun
    assert(loop.DoRun() == 41 && !loop.m_loop);
    assert(!loop.Dispatch() && loop.DispatchTimeout(1) == 0);
    std::puts("pre-run exit and stopped dispatch PASS");

    loop.m_shouldExit = false;
    g_main_context_iteration(NULL, FALSE); // consume the previous quit wakeup
    assert(loop.DispatchTimeout(2) == -1);
    g_idle_add([](gpointer) -> gboolean { return FALSE; }, NULL);
    assert(loop.DispatchTimeout(2) == 1);
    g_usleep(4000);
    assert(!loop.Pending()); // the cancelled timeout must not retain stack data
    std::puts("dispatch timeout and cancellation PASS");

    GThread* thread = g_thread_new("wakeup", [](gpointer p) -> gpointer {
        g_usleep(3000);
        static_cast<wxGUIEventLoop*>(p)->WakeUp();
        return NULL;
    }, &loop);
    assert(loop.DispatchTimeout(1000) == 1);
    g_thread_join(thread);
    std::puts("cross-thread context wakeup without wxApp PASS");

    bool dispatched = false;
    g_idle_add([](gpointer p) -> gboolean { *static_cast<bool*>(p) = true; return FALSE; }, &dispatched);
    assert(!loop.YieldFor(1) && !dispatched && loop.Pending());
    assert(loop.YieldFor(wxEVT_CATEGORY_ALL) && dispatched && loop.yields == 1);
    std::puts("unsupported selective yield leaves input pending; full yield dispatches PASS");

    wxApp app;
    wxTheApp = &app;
    surfaceType = g_type_register_static_simple(G_TYPE_OBJECT, "IdleSurfaceFixture",
        sizeof(GObjectClass), NULL, sizeof(GObject), NULL, GTypeFlags(0));
    gpointer klass = g_type_class_ref(surfaceType);
    g_signal_new("event", surfaceType, G_SIGNAL_RUN_LAST, 0, NULL, NULL, NULL, G_TYPE_NONE, 0);
    g_signal_new("layout", surfaceType, G_SIGNAL_RUN_FIRST, 0, NULL, NULL, NULL, G_TYPE_NONE, 0);
    GObject* surface = G_OBJECT(g_object_new(surfaceType, NULL));
    loop.WakeUp();
    assert(app.m_idleSourceId != 0 && !loop.Pending());
    assert(app.m_idleSourceId == 0); // Pending removes the idle false positive
    g_signal_emit_by_name(surface, "event");
    assert(app.m_idleSourceId != 0);
    assert(loop.Dispatch() && app.idles == 1 && !app.m_idleSourceId);
    g_signal_emit_by_name(surface, "layout");
    assert(loop.Dispatch() && app.idles == 2);
    bool nestedIdle = false;
    app.idleFn = [&] {
        if (nestedIdle) return;
        nestedIdle = true;
        wxGUIEventLoop modal;
        app.WakeUpIdle();
        g_timeout_add(3, QuitLoop, &modal);
        assert(modal.Run() == 31);
    };
    app.WakeUpIdle();
    assert(loop.Dispatch());
    assert(nestedIdle && app.idles == 4 && !app.m_idleSourceId);
    app.idleFn = NULL;
    for (unsigned i = 0; i != 2; ++i) {
        if (gs_idleHooks[i]) g_signal_remove_emission_hook(gs_idleSignals[i], gs_idleHooks[i]);
        gs_idleHooks[i] = 0;
    }
    g_object_unref(surface);
    g_type_class_unref(klass);
    std::puts("one-shot idle event/layout wakeup and nested modal idle PASS");
    app.fail = true;
    g_idle_add(QuitLoop, &loop);
    bool caught = false;
    try { loop.Run(); } catch (const std::runtime_error&) { caught = true; }
    assert(caught && !loop.m_loop && !loop.running && loop.exits == 2);
    std::puts("idle wakeup and stored exception cleanup PASS");
}
