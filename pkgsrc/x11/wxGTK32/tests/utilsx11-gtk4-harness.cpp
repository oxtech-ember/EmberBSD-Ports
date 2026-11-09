// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <stdexcept>
#include <string>
#define __WXGTK__ 1
#define __WXGTK4__ 1
#define GTK_CHECK_VERSION(a,b,c) 1
#define WXUNUSED(x) x
#define wxDECLARE_NO_COPY_CLASS(T) T(const T&) = delete; T& operator=(const T&) = delete
static void Check(bool condition, const char* message);
#define wxASSERT_MSG(condition, message) Check(condition, message)
#define wxS(s) s
#include "wx/gtk/private/object.h"

static void Check(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}
using Window = unsigned long;
using Atom = unsigned long;
using GdkModifierType = unsigned int;
constexpr GdkModifierType GDK_SHIFT_MASK = 1, GDK_CONTROL_MASK = 4, GDK_ALT_MASK = 8;
constexpr bool FALSE = false;
constexpr unsigned GDK_CURRENT_TIME = 0;
struct Display {};
struct Screen {};
struct GdkDevice { GdkModifierType modifiers = 0; bool caps = false, num = false, scroll = false; };
struct GdkSeat { GdkDevice* keyboard = nullptr; };
struct GdkDisplay { GdkSeat* seat = nullptr; Screen screen; };
struct GtkWidget { GdkDisplay* display = nullptr; };
struct GdkAppLaunchContext { GdkDisplay* display; unsigned timestamp = 42; };
#define G_APP_LAUNCH_CONTEXT(c) (c)
enum wxKeyCode { WXK_ALT, WXK_CONTROL, WXK_SHIFT, WXK_CAPITAL, WXK_NUMLOCK, WXK_SCROLL, WXK_UNSUPPORTED };
struct wxString {
    std::string value;
    const char* utf8_str() const { return value.c_str(); }
    template<class... Args> static const char* Format(const char* format, Args...) { return format; }
};
struct wxLaunchBrowserParams { wxString url; };
struct State {
    GdkDisplay* display = nullptr;
    GtkWidget* parent = nullptr;
    Display* knownXDisplay = nullptr;
    GdkDisplay* matchingDisplay = nullptr;
    Screen* expectedScreen = nullptr;
    bool nameMissing = false, hintSupported = false, launchOK = false;
    int atomNames = 0, atomFrees = 0, hints = 0, contexts = 0, unrefs = 0;
    int launches = 0, fallbacks = 0, unsupported = 0, defaultQueries = 0;
    GdkDisplay* launchedDisplay = nullptr;
} state;
#define wxFAIL_MSG(message) (++state.unsupported)

// Only external GTK/GDK/Xlib/GIO operations are substituted. wxGtkObject above
// is the real production owner; a repeated unref is also detected by ASan.
static GdkDisplay* gdk_display_get_default() { ++state.defaultQueries; return state.display; }
static GdkSeat* gdk_display_get_default_seat(GdkDisplay* d) { Check(d, "null display query"); return d->seat; }
static GdkDevice* gdk_seat_get_keyboard(GdkSeat* s) { Check(s, "null seat query"); return s->keyboard; }
static GdkModifierType gdk_device_get_modifier_state(GdkDevice* d) { Check(d, "null keyboard query"); return d->modifiers; }
static bool gdk_device_get_caps_lock_state(GdkDevice* d) { Check(d, "null keyboard caps query"); return d->caps; }
static bool gdk_device_get_num_lock_state(GdkDevice* d) { Check(d, "null keyboard num query"); return d->num; }
static bool gdk_device_get_scroll_lock_state(GdkDevice* d) { Check(d, "null keyboard scroll query"); return d->scroll; }
static GdkDisplay* gdk_x11_lookup_xdisplay(Display* d) { return d == state.knownXDisplay ? state.matchingDisplay : nullptr; }
static char* XGetAtomName(Display* d, Atom atom) {
    Check(d == state.knownXDisplay && atom == 42, "atom uses supplied X display and atom");
    ++state.atomNames;
    if (state.nameMissing) return nullptr;
    const char name[] = "_NET_WM_STATE_FULLSCREEN";
    char* result = static_cast<char*>(std::malloc(sizeof name));
    Check(result != nullptr, "allocation"); std::memcpy(result, name, sizeof name); return result;
}
static int XFree(void* p) { Check(p, "XFree null"); ++state.atomFrees; std::free(p); return 0; }
static Screen* gdk_x11_display_get_screen(GdkDisplay* d) { Check(d == state.matchingDisplay, "WM uses matching display"); return &d->screen; }
static bool gdk_x11_screen_supports_net_wm_hint(Screen* screen, const char* name) {
    Check(screen == state.expectedScreen, "WM screen preserved");
    Check(std::strcmp(name, "_NET_WM_STATE_FULLSCREEN") == 0, "atom name passed intact");
    ++state.hints; return state.hintSupported;
}
static GtkWidget* wxGetTopLevelGTK() { return state.parent; }
static GdkDisplay* gtk_widget_get_display(GtkWidget* w) { Check(w, "null parent query"); return w->display; }
static GdkAppLaunchContext* gdk_display_get_app_launch_context(GdkDisplay* d) { Check(d, "null context display"); ++state.contexts; return new GdkAppLaunchContext{d}; }
static void gdk_app_launch_context_set_timestamp(GdkAppLaunchContext* c, unsigned time) { Check(c, "null context timestamp"); c->timestamp = time; }
static bool g_app_info_launch_default_for_uri(const char* uri, GdkAppLaunchContext* c, void*) {
    Check(std::strcmp(uri, "https://example.invalid/\xD0\xA2?a=1&b=2") == 0, "URI bytes preserved");
    if (c) Check(c->timestamp == GDK_CURRENT_TIME, "startup timestamp set");
    state.launchedDisplay = c ? c->display : nullptr;
    ++state.launches; return state.launchOK;
}
static void g_object_unref(GdkAppLaunchContext* c) { ++state.unrefs; delete c; }

// PRODUCTION_FUNCTIONS

static void Keyboard()
{
    state = {};
    Check(!wxGetKeyStateGTK(WXK_SHIFT), "no display");
    GdkDisplay display; state.display = &display;
    Check(!wxGetKeyStateGTK(WXK_SHIFT), "no seat");
    GdkSeat seat; display.seat = &seat;
    Check(!wxGetKeyStateGTK(WXK_SHIFT), "no keyboard");
    GdkDevice keyboard; seat.keyboard = &keyboard;
    const wxKeyCode keys[] = {WXK_SHIFT, WXK_CONTROL, WXK_ALT};
    const GdkModifierType masks[] = {GDK_SHIFT_MASK, GDK_CONTROL_MASK, GDK_ALT_MASK};
    for (int active = 0; active != 3; ++active) {
        keyboard.modifiers = masks[active];
        for (int i = 0; i != 3; ++i) Check(wxGetKeyStateGTK(keys[i]) == (i == active), "modifier mapping");
    }
    keyboard.modifiers = 0;
    for (wxKeyCode key : keys) Check(!wxGetKeyStateGTK(key), "released modifier");
    const wxKeyCode locks[] = {WXK_CAPITAL, WXK_NUMLOCK, WXK_SCROLL};
    for (int active = -1; active != 3; ++active) {
        keyboard.caps = active == 0; keyboard.num = active == 1; keyboard.scroll = active == 2;
        for (int i = 0; i != 3; ++i) Check(wxGetKeyStateGTK(locks[i]) == (i == active), "lock mapping");
    }
    Check(!wxGetKeyStateGTK(WXK_UNSUPPORTED) && state.unsupported == 1, "unsupported key diagnosed");
}
static void WindowManager()
{
    state = {}; Display known, unknown; GdkDisplay matched;
    state.knownXDisplay = &known; state.matchingDisplay = &matched; state.expectedScreen = &matched.screen;
    Check(!wxQueryWMspecSupport(&unknown, 0, 42) && state.atomNames == 0, "unknown display skips X atom query");
    state.nameMissing = true;
    Check(!wxQueryWMspecSupport(&known, 0, 42) && state.atomFrees == 0 && state.hints == 0, "missing atom is not freed or queried");
    state.nameMissing = false;
    for (bool supported : {false, true}) {
        state.hintSupported = supported;
        const int frees = state.atomFrees;
        Check(wxQueryWMspecSupport(&known, 0, 42) == supported, "WM result propagated");
        Check(state.atomFrees == frees + 1, "atom name freed once");
    }
}
static void Launch()
{
    GdkDisplay primary, alternate; GtkWidget parent{&alternate};
    wxLaunchBrowserParams params{{"https://example.invalid/\xD0\xA2?a=1&b=2"}};
    for (int variant = 0; variant != 3; ++variant) {
        for (bool success : {false, true}) {
            state = {}; state.display = variant == 2 ? nullptr : &primary;
            state.parent = variant == 0 ? &parent : nullptr; state.launchOK = success;
            Check(wxDoLaunchDefaultBrowser(params) == success, "launch result propagated");
            Check(state.launchedDisplay == (variant == 0 ? &alternate : variant == 1 ? &primary : nullptr), "parent/default/no-display launch");
            Check(state.defaultQueries == (variant == 0 ? 0 : 1), "parent display takes precedence");
            Check(state.launches == 1 && state.fallbacks == (success ? 0 : 1), "success returns and failure reaches existing fallback");
            Check(state.contexts == (variant == 2 ? 0 : 1) && state.unrefs == state.contexts, "launch context released once on both outcomes");
        }
    }
}
int main()
{
    try { Keyboard(); WindowManager(); Launch(); }
    catch (const std::exception& error) { std::fprintf(stderr, "%s\n", error.what()); return 1; }
    std::puts("PASS: production GTK4 utility branches, external API ownership and URI fallback boundary");
}
