// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/popupwin.h>
#include <wx/textctrl.h>
#include <wx/timer.h>
#include <wx/weakref.h>
#include <gtk/gtk.h>
#include <cstdio>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif

static void Check(bool value, const char* message)
{ if (!value) throw std::runtime_error(message); }

class Transient : public wxPopupTransientWindow
{
public:
    int dismissed = 0;
    explicit Transient(wxWindow* owner) : wxPopupTransientWindow(owner) { }
    void OnDismiss() wxOVERRIDE { ++dismissed; }
};

class DismissOnFocus : public wxTextCtrl
{
    Transient* popup;
    bool first = true;
public:
    explicit DismissOnFocus(Transient* owner)
        : wxTextCtrl(owner, wxID_ANY), popup(owner) { }
    void SetFocus() wxOVERRIDE
    {
        if (first)
        {
            first = false;
            popup->Dismiss();
        }
        else
            wxTextCtrl::SetFocus();
    }
};

class DeleteOnFocus : public wxTextCtrl
{
public:
    explicit DeleteOnFocus(wxWindow* owner) : wxTextCtrl(owner, wxID_ANY) { }
    void SetFocus() wxOVERRIDE { delete this; }
};

class PopupContract : public wxApp
{
    wxFrame* frame = NULL;
    wxTimer timer;
    int result = 1;
    int ticks = 0;
public:
    bool OnInit() wxOVERRIDE
    {
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 popup contract",
                            wxDefaultPosition, wxSize(400, 300));
        SetTopWindow(frame);
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { RunChecks(); });
        frame->Show();
        timer.Start(100);
        return true;
    }
    int OnRun() wxOVERRIDE { wxApp::OnRun(); return result; }
    void RunChecks()
    {
        if (!gtk_widget_get_mapped(frame->m_wxwindow) && ++ticks < 50) return;
        timer.Stop();
        try
        {
            Check(gtk_widget_get_mapped(frame->m_wxwindow), "real mapped owner required");
            wxPopupWindow* plain = new wxPopupWindow(frame);
            plain->SetSize(140, 80);
            plain->Position(frame->ClientToScreen(wxPoint(20, 20)), wxSize(0, 20));
            Check(plain->Show(), "plain popup maps");
            Check(GTK_IS_POPOVER(plain->m_widget) &&
                  !gtk_popover_get_autohide(GTK_POPOVER(plain->m_widget)),
                  "ordinary popup must not acquire transient input grab");
            GdkSurface* surface = gtk_native_get_surface(GTK_NATIVE(plain->m_widget));
            Check(surface && GDK_IS_POPUP(surface), "popup owns a real GdkPopup surface");
            Check(gdk_popup_get_parent(GDK_POPUP(surface)) ==
                  gtk_native_get_surface(gtk_widget_get_native(frame->m_wxwindow)),
                  "popup surface belongs to the actual owner");
            Check(plain->GetPosition() == plain->ClientToScreen(wxPoint(0, 0)),
                  "mapped popup reports compositor-adjusted surface position");
            plain->Hide();
            delete plain;

            // The documented null-parent API uses the existing application
            // top window, without allocating a hidden second GtkWindow.
            wxPopupWindow* parentless = new wxPopupWindow(NULL);
            parentless->SetSize(100, 60);
            parentless->Position(frame->ClientToScreen(wxPoint(10, 10)), wxSize(0, 0));
            Check(parentless->GetParent() == NULL && parentless->Show(), "parentless popup owner");
            delete parentless;

            Transient* popup = new Transient(frame);
            popup->SetSize(160, 90);
            wxTextCtrl* input = new wxTextCtrl(popup, wxID_ANY, "Editable child");
            input->SetSize(0, 0, 150, 40);
            popup->Position(frame->ClientToScreen(wxPoint(30, 30)), wxSize(0, 20));
            popup->Popup(input);
            Check(popup->IsShown() && gtk_popover_get_autohide(GTK_POPOVER(popup->m_widget)),
                  "transient popup uses GTK's native dismissal and grab");
            popup->Dismiss();
            Check(!popup->IsShown() && popup->dismissed == 0, "explicit dismissal does not notify");
            for (int pass = 1; pass <= 2; ++pass)
            {
                popup->Popup(input);
                gtk_popover_popdown(GTK_POPOVER(popup->m_widget));
                Check(!popup->IsShown() && popup->dismissed == pass,
                      "native dismissal notifies once and permits reuse");
            }
            delete popup;

            Transient* focusDismiss = new Transient(frame);
            focusDismiss->SetSize(160, 90);
            DismissOnFocus* focus = new DismissOnFocus(focusDismiss);
            focusDismiss->Popup(focus);
            Check(!focusDismiss->IsShown(), "focus callback dismisses popup");
            focusDismiss->Popup(focus);
            Check(focusDismiss->IsShown(), "dismissal during focus leaves no stale handlers");
            focusDismiss->Dismiss();
            delete focusDismiss;

            Transient* focusRemoved = new Transient(frame);
            focusRemoved->SetSize(160, 90);
            DeleteOnFocus* disappearing = new DeleteOnFocus(focusRemoved);
            wxWeakRef<DeleteOnFocus> childAlive(disappearing);
            focusRemoved->Popup(disappearing);
            Check(!childAlive && focusRemoved->IsShown(),
                  "focus callback may delete its own child before handlers attach");
            focusRemoved->Dismiss();
            delete focusRemoved;

            Transient* childRemoved = new Transient(frame);
            childRemoved->SetSize(120, 80);
            wxTextCtrl* removedFocus = new wxTextCtrl(childRemoved, wxID_ANY);
            childRemoved->Bind(wxEVT_SHOW, [removedFocus](wxShowEvent& event) {
                if (event.IsShown()) delete removedFocus;
            });
            childRemoved->Popup(removedFocus);
            Check(childRemoved->IsShown() && childRemoved->GetChildren().IsEmpty(),
                  "Show callback may remove capture child and requested focus");
            childRemoved->Dismiss();
            delete childRemoved;

            Transient* destroyedOnSize = new Transient(frame);
            wxWeakRef<Transient> sizeAlive(destroyedOnSize);
            g_signal_connect(destroyedOnSize->m_wxwindow, "notify::width-request",
                G_CALLBACK(+[](GObject*, GParamSpec*, gpointer data) {
                    delete static_cast<Transient*>(data);
                }), destroyedOnSize);
            destroyedOnSize->SetSize(123, 77);
            Check(!sizeAlive, "native size notification may destroy the popup");

            Transient* destroyedOnAutohide = new Transient(frame);
            wxWeakRef<Transient> autohideAlive(destroyedOnAutohide);
            destroyedOnAutohide->SetSize(100, 60);
            g_signal_connect(destroyedOnAutohide->m_widget, "notify::autohide",
                G_CALLBACK(+[](GObject*, GParamSpec*, gpointer data) {
                    delete static_cast<Transient*>(data);
                }), destroyedOnAutohide);
            destroyedOnAutohide->Popup();
            Check(!autohideAlive, "native autohide notification may destroy the popup");

            Transient* destroyedOnShow = new Transient(frame);
            wxWeakRef<Transient> showAlive(destroyedOnShow);
            destroyedOnShow->SetSize(100, 60);
            destroyedOnShow->Bind(wxEVT_SHOW, [destroyedOnShow](wxShowEvent& event) {
                if (event.IsShown()) delete destroyedOnShow;
            });
            destroyedOnShow->Popup();
            Check(!showAlive, "destruction from Show callback must abort Popup safely");

            Transient* destroyedOnHide = new Transient(frame);
            wxWeakRef<Transient> hideAlive(destroyedOnHide);
            destroyedOnHide->SetSize(100, 60);
            destroyedOnHide->Popup();
            destroyedOnHide->Bind(wxEVT_SHOW, [destroyedOnHide](wxShowEvent& event) {
                if (!event.IsShown()) delete destroyedOnHide;
            });
            GtkPopover* native = GTK_POPOVER(g_object_ref(destroyedOnHide->m_widget));
            gtk_popover_popdown(native);
            g_object_unref(native);
            Check(!hideAlive, "destruction from native dismissal must not continue through dead wx state");

            result = 0;
            std::puts("GTK4 popup ownership, position, dismissal and callback lifetime passed");
        }
        catch (const std::exception& error)
        { std::fprintf(stderr, "%s\n", error.what()); }
        frame->Destroy();
        ExitMainLoop();
    }
};
wxIMPLEMENT_APP_NO_MAIN(PopupContract);
int main(int argc, char** argv) { return wxEntry(argc, argv); }
