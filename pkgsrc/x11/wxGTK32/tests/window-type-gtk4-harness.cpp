// SPDX-License-Identifier: BSD-2-Clause
// Actual production EWMH helpers with only the GtkWindow/display boundary mocked.
#include <glib-object.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unordered_map>

struct GdkDisplay { bool isX11; };
struct GtkWindow {};
using GtkWidget = GtkWindow;
struct WindowState { bool mapped; GdkDisplay* display; };
static std::unordered_map<GtkWidget*, WindowState> windowStates;
static gboolean gtk_widget_get_mapped(GtkWidget* widget) { return windowStates[widget].mapped; }
static GdkDisplay* gtk_widget_get_display(GtkWidget* widget) { return windowStates[widget].display; }
#define GDK_WINDOWING_X11 1
#define GDK_IS_X11_DISPLAY(display) ((display)->isX11)
#define GTK_WIDGET(window) (window)

// PRODUCTION_WINDOW_TYPE_HELPERS

static void Check(bool ok, const char* message)
{
    if (ok) return;
    std::fprintf(stderr, "FAIL: %s\n", message);
    std::abort();
}

int main()
{
    GdkDisplay x11 = { true };
    GdkDisplay wayland = { false };
    GObject* x11Object = static_cast<GObject*>(g_object_new(G_TYPE_OBJECT, NULL));
    GObject* waylandObject = static_cast<GObject*>(g_object_new(G_TYPE_OBJECT, NULL));
    GObject* mappedObject = static_cast<GObject*>(g_object_new(G_TYPE_OBJECT, NULL));
    GtkWindow* x11Window = reinterpret_cast<GtkWindow*>(x11Object);
    GtkWindow* waylandWindow = reinterpret_cast<GtkWindow*>(waylandObject);
    GtkWindow* mappedWindow = reinterpret_cast<GtkWindow*>(mappedObject);
    windowStates[x11Window] = { false, &x11 };
    windowStates[waylandWindow] = { false, &wayland };
    windowStates[mappedWindow] = { true, &x11 };
    const char* splash = "_NET_WM_WINDOW_TYPE_SPLASH";
    const char* dialog = "_NET_WM_WINDOW_TYPE_DIALOG";
    char mutableAtom[] = "_NET_WM_WINDOW_TYPE_UTILITY";

    Check(wxGTKWindowState4::GetRequestedWindowType(NULL) == NULL, "null window has no stored request");
    Check(!wxGTKWindowState4::RequestWindowType(NULL, splash), "null window request is refused");
    Check(!wxGTKWindowState4::RequestWindowType(x11Window, NULL), "null atom request is refused");
    Check(!wxGTKWindowState4::RequestWindowType(x11Window, ""), "empty atom request is refused");
    Check(wxGTKWindowState4::GetRequestedWindowType(x11Window) == NULL, "refused request stores no qdata");
    Check(wxGTKWindowState4::RequestWindowType(x11Window, mutableAtom), "X11 request is accepted before map");
    mutableAtom[0] = 'x';
    Check(std::strcmp(wxGTKWindowState4::GetRequestedWindowType(x11Window), "_NET_WM_WINDOW_TYPE_UTILITY") == 0,
          "request owns a copy of the atom name");
    Check(wxGTKWindowState4::RequestWindowType(x11Window, splash), "replacement X11 request is accepted");
    Check(std::strcmp(wxGTKWindowState4::GetRequestedWindowType(x11Window), splash) == 0,
          "new request replaces the old qdata");
    Check(!wxGTKWindowState4::RequestWindowType(waylandWindow, splash), "Wayland does not claim EWMH support");
    Check(wxGTKWindowState4::GetRequestedWindowType(waylandWindow) == NULL,
          "Wayland refusal leaves no qdata");
    Check(!wxGTKWindowState4::RequestWindowType(mappedWindow, dialog), "mapped windows refuse pre-map requests");
    Check(wxGTKWindowState4::GetRequestedWindowType(mappedWindow) == NULL,
          "mapped-window refusal leaves no qdata");

    g_object_unref(x11Object);
    g_object_unref(waylandObject);
    g_object_unref(mappedObject);
    windowStates.clear();
    std::puts("PASS: production GTK4 EWMH request copy, replacement, and backend guards");
    return 0;
}
