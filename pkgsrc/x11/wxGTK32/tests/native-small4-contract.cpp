// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/bitmap.h>
#include <wx/cursor.h>
#include <wx/image.h>
#include <wx/mdi.h>
#include <wx/menu.h>
#include <wx/nativewin.h>
#include <wx/timer.h>
#include <wx/log.h>
#include <gtk/gtk.h>
#include <cstdio>
#include <stdexcept>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
#ifdef wxHAS_NATIVE_CONTAINER_WINDOW
#error GTK4 must not advertise unsupported foreign surface embedding.
#endif
#ifndef wxHAS_NATIVE_WINDOW
#error GTK4 must retain native child widget embedding.
#endif
static void Check(bool value, const char* message)
{ if (!value) throw std::runtime_error(message); }
static void Finalized(gpointer data, GObject*)
{ *static_cast<bool*>(data) = true; }
class NativeSmallContract : public wxApp
{
    wxMDIParentFrame* frame = NULL;
    wxMDIChildFrame* child = NULL;
    wxTimer timer;
    int result = 1;
    void Run()
    {
        timer.Stop();
        try
        {
            wxBitmap recovered;
            {
                wxImage image(8, 8);
                image.SetRGB(wxRect(0, 0, 8, 8), 255, 0, 0);
                image.InitAlpha();
                image.SetAlpha(2, 3, 128);
                image.SetOption(wxIMAGE_OPTION_CUR_HOTSPOT_X, 2);
                image.SetOption(wxIMAGE_OPTION_CUR_HOTSPOT_Y, 3);
                wxCursor cursor(image);
                recovered = wxBitmap(cursor);
                Check(recovered.IsOk(), "custom cursor has a bitmap");
                Check(gdk_cursor_get_texture(cursor.GetCursor()) != NULL,
                      "bitmap conversion leaves the borrowed cursor texture alive");
            }
            wxImage pixels = recovered.ConvertToImage();
            Check(pixels.IsOk() && pixels.GetWidth() == 8 && pixels.GetHeight() == 8,
                  "bitmap retains dimensions after cursor destruction");
            Check(pixels.GetRed(2, 3) == 255 && pixels.GetGreen(2, 3) == 0 &&
                  pixels.GetBlue(2, 3) == 0 && pixels.HasAlpha() && pixels.GetAlpha(2, 3) == 128,
                  "cursor bitmap preserves RGBA pixels");
            Check(!wxBitmap(wxCursor(wxCURSOR_ARROW)).IsOk(),
                  "named cursor does not fabricate a bitmap");
            Check(!wxBitmap(wxCursor()).IsOk(), "invalid cursor leaves an invalid bitmap");

            GtkWidget* retained = gtk_button_new_with_label("Retained native widget");
            wxNativeWindow* wrapper = new wxNativeWindow(child, wxID_ANY, retained);
            Check(wrapper->GetHandle() == retained && wrapper->GetSize().x > 0 &&
                  wrapper->GetSize().y > 0, "native widget is parented and measured");
            delete wrapper;
            Check(!gtk_widget_get_parent(retained), "caller-owned native widget survives wrapper deletion");
            gtk_button_set_label(GTK_BUTTON(retained), "Still alive");
            g_object_unref(retained);

            static bool retainedFinalized = false;
            retainedFinalized = false;
            retained = gtk_button_new_with_label("Already owned native widget");
            g_object_ref_sink(retained);
            g_object_weak_ref(G_OBJECT(retained), Finalized, &retainedFinalized);
            wrapper = new wxNativeWindow(child, wxID_ANY, retained);
            delete wrapper;
            Check(!retainedFinalized && !gtk_widget_get_parent(retained),
                  "non-floating caller reference survives wrapper deletion");
            g_object_unref(retained);
            Check(retainedFinalized, "non-floating wrapping does not leak another caller reference");

            static bool finalized = false;
            finalized = false;
            GtkWidget* owned = gtk_button_new_with_label("Transferred native widget");
            g_object_weak_ref(G_OBJECT(owned), Finalized, &finalized);
            wrapper = new wxNativeWindow(child, wxID_ANY, owned);
            wrapper->Disown();
            Check(!finalized, "Disown retains the native widget until wrapper destruction");
            delete wrapper;
            Check(finalized, "Disown releases the last native reference with its wrapper");

            GtkWidget* bar = GTK_WIDGET(child->GetMenuBar()->GetHandle());
            Check(gtk_widget_get_parent(bar) == frame->m_mainWidget &&
                  gtk_widget_get_first_child(frame->m_mainWidget) == bar,
                  "MDI child menu is prepended to the parent box");
            Check(!gtk_widget_get_vexpand(bar), "MDI menu does not consume client vertical space");
            Check(frame->GetActiveChild() == child && frame->GetClientSize().y > 0,
                  "MDI activation retains usable client geometry");
            result = 0;
            std::puts("GTK4 cursor bitmap, native widget ownership and MDI contracts PASS");
        }
        catch (const std::exception& error)
        { std::fprintf(stderr, "%s\n", error.what()); }
        frame->Destroy();
        ExitMainLoop();
    }
public:
    bool OnInit() override
    {
        wxLog::SetActiveTarget(new wxLogStderr);
        frame = new wxMDIParentFrame(NULL, wxID_ANY, "GTK4 native contracts",
                                    wxDefaultPosition, wxSize(640, 480));
        child = new wxMDIChildFrame(frame, wxID_ANY, "Document");
        wxMenuBar* bar = new wxMenuBar;
        wxMenu* menu = new wxMenu;
        menu->Append(wxID_OPEN, "&Open");
        bar->Append(menu, "&File");
        child->SetMenuBar(bar);
        child->Show();
        frame->Show();
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Run(); });
        timer.StartOnce(500);
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(NativeSmallContract);
