// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/aboutdlg.h>
#include <wx/frame.h>
#include <wx/image.h>
#include <gtk/gtk.h>
#include <cstdio>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif

static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }

// Return an owned reference so delayed disposal can also be exercised.
static GtkAboutDialog* FindAbout()
{
    GListModel* windows = gtk_window_get_toplevels();
    GtkAboutDialog* result = NULL;
    unsigned count = 0;
    for (guint i = 0; i < g_list_model_get_n_items(windows); ++i)
    {
        auto window = G_OBJECT(g_list_model_get_item(windows, i));
        if (GTK_IS_ABOUT_DIALOG(window))
        {
            ++count;
            if (!result) result = GTK_ABOUT_DIALOG(g_object_ref(window));
        }
        g_object_unref(window);
    }
    if (count != 1)
    {
        if (result) g_object_unref(result);
        throw std::runtime_error("expected exactly one native about window");
    }
    return result;
}

class AboutContract : public wxApp
{
    wxFrame* parent = NULL;
    int status = 1;
    void Run()
    {
        GtkAboutDialog *old = NULL, *current = NULL;
        try
        {
            wxAboutDialogInfo info;
            info.SetName("About contract");
            info.SetVersion("1.0");
            info.SetWebSite("https://www.wxwidgets.org/", "Project");
            wxImage image(2, 2);
            image.SetRGB(wxRect(0, 0, 2, 2), 255, 0, 0);
            wxIcon icon;
            icon.CopyFromBitmap(wxBitmap(image));
            info.SetIcon(icon);
            wxAboutBox(info, parent);
            old = FindAbout();
            Check(gtk_window_get_transient_for(GTK_WINDOW(old)) == GTK_WINDOW(parent->GetHandle()),
                  "native about window retains its parent");
            Check(gtk_about_dialog_get_logo(old) != NULL, "logo uses a native paintable");

            wxAboutDialogInfo updated;
            updated.SetName("Updated about contract");
            wxAboutBox(updated, parent);
            current = FindAbout();
            Check(current == old, "repeated invocation reuses the open window");
            Check(wxString::FromUTF8(gtk_about_dialog_get_program_name(current)) == updated.GetName(),
                  "cached window receives current metadata");
            Check(!gtk_about_dialog_get_version(current) && !gtk_about_dialog_get_website(current),
                  "old optional metadata is cleared");
            Check(!updated.GetIcon().IsOk() && !gtk_about_dialog_get_logo(current),
                  "old paintable is cleared when no icon is supplied");
            g_clear_object(&current);

            gtk_window_close(GTK_WINDOW(old));
            Check(!gtk_widget_get_visible(GTK_WIDGET(old)), "native close hides the old window");
            wxAboutBox(info, parent);
            current = FindAbout();
            Check(current != old, "close invalidates the cache even while an external reference survives");
            g_clear_object(&old); // Late destruction must not clear the new cache.
            wxAboutBox(updated, parent);
            old = FindAbout();
            Check(old == current, "late destruction preserves the current cached window");
            g_clear_object(&old);
            gtk_window_destroy(GTK_WINDOW(current));
            wxAboutBox(info, parent);
            old = FindAbout();
            Check(old != current, "direct native destruction invalidates the cached toplevel");
            g_clear_object(&current);
            wxAboutBox(updated, parent);
            current = FindAbout();
            Check(current == old, "late disposal after direct destruction preserves the new cache");
            g_clear_object(&old);
            g_signal_emit_by_name(current, "force-close");
            Check(!gtk_widget_get_visible(GTK_WIDGET(current)), "compositor close releases the native window");
            g_clear_object(&current);
            wxAboutBox(updated, parent);
            current = FindAbout();
            gtk_window_close(GTK_WINDOW(current));
            status = 0;
            std::puts("GTK4 about metadata, paintable and close contracts PASS");
        }
        catch (const std::exception& error)
        { std::fprintf(stderr, "FAIL: %s\n", error.what()); }
        if (old) { gtk_window_destroy(GTK_WINDOW(old)); g_object_unref(old); }
        if (current) { gtk_window_destroy(GTK_WINDOW(current)); g_object_unref(current); }
        parent->Destroy();
    }
public:
    bool OnInit() wxOVERRIDE
    {
        parent = new wxFrame(NULL, wxID_ANY, "GTK4 about contract");
        SetTopWindow(parent);
        parent->Show();
        CallAfter([this]() { Run(); });
        return true;
    }
    int OnExit() wxOVERRIDE { return status; }
};
wxIMPLEMENT_APP(AboutContract);
