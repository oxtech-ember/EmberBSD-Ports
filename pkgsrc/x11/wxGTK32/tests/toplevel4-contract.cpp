// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Requires a real GTK4 desktop with a window manager/compositor.
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/log.h>
#include <wx/menu.h>
#include <wx/timer.h>
#include <wx/weakref.h>
#include <wx/minifram.h>
#include <gtk/gtk.h>
#ifdef GDK_WINDOWING_X11
#include <gdk/x11/gdkx.h>
#include <X11/Xutil.h>
#endif
#include <cstdio>
#include <stdexcept>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }

class ToplevelContract : public wxApp
{
    wxWeakRef<wxFrame> frame;
    wxWeakRef<wxMiniFrame> mini;
    wxTimer timer;
    int stage = 0, ticks = 0, closeEvents = 0, shows = 0, hides = 0, result = 1;
    wxSize outer;
    bool finished = false;
    void Finish(int status, const char* message)
    {
        if (finished) return;
        finished = true;
        timer.Stop();
        result = status;
        std::fprintf(status ? stderr : stdout, "%s\n", message);
        if (frame) frame->Destroy();
        ExitMainLoop();
    }
    void Next() { ++stage; ticks = 0; }
    void CheckIncrements(bool explicitIncrements)
    {
#ifdef GDK_WINDOWING_X11
        GdkSurface* surface = gtk_native_get_surface(GTK_NATIVE(frame->GetHandle()));
        if (!GDK_IS_X11_SURFACE(surface)) return;
        XSizeHints hints = {};
        long supplied;
        Check(XGetWMNormalHints(gdk_x11_display_get_xdisplay(gdk_surface_get_display(surface)),
            gdk_x11_surface_get_xid(surface), &hints, &supplied), "native WM size hints exist");
        const double scale = gdk_surface_get_scale(surface);
        if (explicitIncrements)
            Check((hints.flags & PResizeInc) && hints.width_inc == wxRound(7 * scale) &&
                  hints.height_inc == wxRound(9 * scale), "native resize increments applied after GTK layout");
        else
            Check(!(hints.flags & PResizeInc) ||
                  (hints.width_inc == wxRound(scale) && hints.height_inc == wxRound(scale)),
                  "reset increments removes stale application WM hints");
#else
        wxUnusedVar(explicitIncrements);
#endif
    }
    void Step()
    {
        try
        {
            if (++ticks > 100) throw std::runtime_error("native state/geometry transition timeout");
            Check(frame.get() != NULL, "main frame unexpectedly destroyed");
            switch (stage)
            {
            case 0:
                if (!gtk_widget_get_mapped(GTK_WIDGET(frame->GetHandle())) ||
                    frame->GetClientSize() != wxSize(360, 240)) return;
#ifdef GDK_WINDOWING_X11
                {
                    GdkSurface* surface = gtk_native_get_surface(GTK_NATIVE(frame->GetHandle()));
                    if (GDK_IS_X11_SURFACE(surface) &&
                        !(gdk_toplevel_get_state(GDK_TOPLEVEL(surface)) & GDK_TOPLEVEL_STATE_ABOVE)) return;
                }
#endif
                outer = frame->GetSize();
                frame->SetSize(outer);
                Next(); return;
            case 1:
                if (ticks < 3) return;
                Check(frame->GetSize() == outer && frame->GetClientSize() == wxSize(360, 240),
                      "SetSize(GetSize()) must not accumulate CSD/shadow extents");
                frame->SetClientSize(420, 280);
                Next(); return;
            case 2:
                if (frame->GetClientSize() != wxSize(420, 280)) return;
                outer = frame->GetSize();
                frame->Hide(); frame->Show();
                Next(); return;
            case 3:
            {
                if (ticks < 3) return;
                Check(frame->GetSize() == outer, "hide/show retains measured geometry");
                Check(shows == 2 && hides == 1, "one wx show event per visibility change");
                GtkWindow* native = GTK_WINDOW(frame->GetHandle());
                gboolean handled = FALSE;
                frame->EnableCloseButton(false);
                g_signal_emit_by_name(native, "close-request", &handled);
                Check(handled && closeEvents == 0, "disabled close button blocks close request");
                frame->EnableCloseButton(true);
                g_signal_emit_by_name(native, "close-request", &handled);
                Check(handled && closeEvents == 1 && frame->IsShown(), "wx close veto keeps native window alive");
                frame->SetSizeHints(-1, -1, -1, -1, 7, 9);
                CheckIncrements(true);
                frame->SetSizeHints(-1, -1, -1, -1, 0, 0);
                Next(); return;
            }
            case 4:
                if (ticks < 3) return;
                CheckIncrements(false);
                frame->Maximize();
                Next(); return;
            case 5:
                if (!frame->IsMaximized()) return;
                frame->Restore();
                Next(); return;
            case 6:
                if (frame->IsMaximized()) return;
                frame->ShowFullScreen(true);
                Next(); return;
            case 7:
                if (!gtk_window_is_fullscreen(GTK_WINDOW(frame->GetHandle()))) return;
                frame->ShowFullScreen(false);
                Next(); return;
            case 8:
                if (gtk_window_is_fullscreen(GTK_WINDOW(frame->GetHandle()))) return;
                frame->Iconize();
                Next(); return;
            case 9:
                if (!frame->IsIconized()) return;
                frame->Restore();
                Next(); return;
            case 10:
                if (frame->IsIconized()) return;
                timer.Stop();
                // Nested loop and restoration use the real wx/GLib event loop.
                CallAfter([this]() { frame->RemoveGrab(); });
                frame->AddGrab();
                Check(!frame->IsGrabbed() && !gtk_window_get_modal(GTK_WINDOW(frame->GetHandle())),
                      "explicit modal grab exits and restores native modal state");
                Next(); timer.Start(100); return;
            case 11:
                mini = new wxMiniFrame(frame.get(), wxID_ANY, "GTK4 utility frame",
                    wxDefaultPosition, wxDefaultSize, wxCAPTION | wxRESIZE_BORDER | wxCLOSE_BOX);
                mini->SetClientSize(220, 140);
                mini->Show();
                Next(); return;
            case 12:
            {
                Check(mini.get() != NULL, "utility frame remains alive");
                if (!gtk_widget_get_mapped(GTK_WIDGET(mini->GetHandle())) ||
                    mini->GetClientSize() != wxSize(220, 140)) return;
                GtkWindow* native = GTK_WINDOW(mini->GetHandle());
                Check(gtk_window_get_transient_for(native) == GTK_WINDOW(frame->GetHandle()),
                      "utility frame retains native parent relationship");
                Check(gtk_window_get_resizable(native) && gtk_window_get_deletable(native),
                      "utility frame retains resize and close capabilities");
                mini->SetTitle("Updated utility title");
                Check(wxString::FromUTF8(gtk_window_get_title(native)) == "Updated utility title",
                      "utility title updates through native frame");
                mini->Destroy();
                Next(); return;
            }
            case 13:
            {
                timer.Stop();
                wxFrame* transient = new wxFrame(frame.get(), wxID_ANY, "Destroy during grab");
                wxWeakRef<wxFrame> weak(transient);
                transient->Show();
                CallAfter([transient]() { delete transient; });
                transient->AddGrab();
                Check(!weak, "owner destruction exits the synchronous grab safely");
                wxFrame* closing = new wxFrame(frame.get(), wxID_ANY, "Destroy in close callback");
                wxWeakRef<wxFrame> closed(closing);
                GtkWindow* native = GTK_WINDOW(g_object_ref(closing->GetHandle()));
                closing->Bind(wxEVT_CLOSE_WINDOW, [closing](wxCloseEvent&) { delete closing; });
                gboolean handled = FALSE;
                g_signal_emit_by_name(native, "close-request", &handled);
                Check(handled && !closed, "synchronous wx destruction during native close callback");
                g_object_unref(native);
                wxFrame* forced = new wxFrame(frame.get(), wxID_ANY, "Compositor force close");
                wxWeakRef<wxFrame> forcedWeak(forced);
                GtkWindow* forcedNative = GTK_WINDOW(g_object_ref(forced->GetHandle()));
                bool nonVetoable = false;
                forced->Bind(wxEVT_CLOSE_WINDOW, [&nonVetoable](wxCloseEvent& e)
                    { nonVetoable = !e.CanVeto(); });
                forced->Show();
                g_signal_emit_by_name(forcedNative, "force-close");
                Check(nonVetoable && !gtk_widget_get_visible(GTK_WIDGET(forcedNative)) &&
                      (!forcedWeak || forcedWeak->IsBeingDeleted()),
                      "compositor force-close hides and schedules wx-owned destruction");
                g_object_unref(forcedNative);
                Finish(0, "GTK4 top-level geometry, veto, state and destruction contracts PASS");
                return;
            }
            }
        }
        catch (const std::exception& e) { Finish(1, e.what()); }
    }
public:
    bool OnInit() override
    {
        wxLog::SetActiveTarget(new wxLogStderr);
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 top-level contract", wxDefaultPosition,
                            wxDefaultSize, wxDEFAULT_FRAME_STYLE | wxSTAY_ON_TOP);
        frame->Bind(wxEVT_SHOW, [this](wxShowEvent& e)
            { if (e.IsShown()) ++shows; else ++hides; e.Skip(); });
        frame->Bind(wxEVT_CLOSE_WINDOW, [this](wxCloseEvent& e) { ++closeEvents; e.Veto(); });
        frame->CreateStatusBar();
        auto bar = new wxMenuBar;
        auto menu = new wxMenu;
        menu->Append(wxID_ABOUT, "&About");
        bar->Append(menu, "&Test");
        frame->SetMenuBar(bar);
        // Includes frame bars: only the actual client area should be 360x240.
        frame->SetClientSize(360, 240);
        frame->Show();
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Step(); });
        timer.Start(100);
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(ToplevelContract);
