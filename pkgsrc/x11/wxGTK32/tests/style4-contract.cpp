// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Run on the built GTK4 backend with G_DEBUG=fatal-warnings and a real display.
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/settings.h>
#include <wx/renderer.h>
#include <wx/dcmemory.h>
#include <wx/dcgraph.h>
#include <wx/gtk/private.h>
#include <cstdio>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif

static void Check(bool value, const char* message)
{
    if (!value) throw std::runtime_error(message);
}

class StyleContract : public wxApp
{
    wxFrame* frame = NULL;
    int result = 1;
public:
    bool OnInit() wxOVERRIDE
    {
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 style contract");
        frame->Show();
        CallAfter([this] { RunChecks(); });
        return true;
    }
    int OnRun() wxOVERRIDE
    {
        wxApp::OnRun();
        return result;
    }
    void RunChecks()
    {
        try
        {
            Check(gdk_display_get_default() != NULL, "real GTK display required");
            Check(wxSystemSettings::GetColour(wxSYS_COLOUR_WINDOW).IsOk(), "window colour");
            Check(wxSystemSettings::GetColour(wxSYS_COLOUR_WINDOWTEXT).IsOk(), "text colour");
            Check(wxSystemSettings::GetColour(wxSYS_COLOUR_HIGHLIGHT).IsOk(), "selection colour");
            Check(wxSystemSettings::GetFont(wxSYS_DEFAULT_GUI_FONT).IsOk(), "native font");
            Check(wxSystemSettings::GetMetric(wxSYS_VSCROLL_X, frame) > 0, "measured scrollbar width");
            wxRendererNative& renderer = wxRendererNative::Get();
            const wxSize checkbox = renderer.GetCheckBoxSize(frame);
            Check(checkbox.x > 0 && checkbox.y > 0, "measured checkbox size");
            Check(renderer.GetHeaderButtonHeight(frame) > 0, "measured column header height");
            GtkStyleContext* buttonStyle = gtk_widget_get_style_context(wxGTKPrivate::GetButtonWidget());
            const GtkStateFlags initialState = gtk_style_context_get_state(buttonStyle);
            wxBitmap bitmap(160, 64, 32);
            {
                wxMemoryDC memory(bitmap);
                wxGCDC dc(memory);
                renderer.DrawPushButton(frame, dc, wxRect(0, 0, 70, 32), wxCONTROL_PRESSED);
                renderer.DrawPushButton(frame, dc, wxRect(75, 0, 70, 32), wxCONTROL_DISABLED);
                renderer.DrawCheckBox(frame, dc, wxRect(0, 34, 24, 24), wxCONTROL_CHECKED);
                renderer.DrawRadioBitmap(frame, dc, wxRect(30, 34, 24, 24), wxCONTROL_CHECKED);
            }
            Check(gtk_style_context_get_state(buttonStyle) == initialState,
                  "scoped drawing must restore cached widget state");
            // Exercise cache invalidation with the actual GTK setting. A custom
            // theme may ignore the preference, so no particular RGB is assumed.
            GtkSettings* settings = gtk_settings_get_default();
            gboolean preferDark = FALSE;
            g_object_get(settings, "gtk-application-prefer-dark-theme", &preferDark, NULL);
            g_object_set(settings, "gtk-application-prefer-dark-theme", !preferDark, NULL);
            Check(wxSystemSettings::GetColour(wxSYS_COLOUR_WINDOW).IsOk(), "theme-change colour query");
            g_object_set(settings, "gtk-application-prefer-dark-theme", preferDark, NULL);
            result = 0;
            std::puts("GTK4 native theme, metrics and scoped rendering passed");
        }
        catch (const std::exception& error)
        {
            std::fprintf(stderr, "%s\n", error.what());
        }
        frame->Destroy();
        ExitMainLoop();
    }
};
wxIMPLEMENT_APP_NO_MAIN(StyleContract);
int main(int argc, char** argv) { return wxEntry(argc, argv); }
