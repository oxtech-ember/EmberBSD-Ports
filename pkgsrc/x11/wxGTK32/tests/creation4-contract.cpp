// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/spinctrl.h>
#include <gtk/gtk.h>
#include <cmath>
#include <cstdio>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif

static void Check(bool ok, const char* message)
{
    if (!ok) throw std::runtime_error(message);
}

class CreationContract : public wxApp
{
    wxFrame* frame = NULL;
    int result = 1;
    GLogLevelFlags previousFatal;

public:
    bool OnInit() wxOVERRIDE
    {
        previousFatal = g_log_set_always_fatal(
            static_cast<GLogLevelFlags>(G_LOG_FATAL_MASK | G_LOG_LEVEL_CRITICAL));
        g_log_set_always_fatal(static_cast<GLogLevelFlags>(
            previousFatal | G_LOG_FATAL_MASK | G_LOG_LEVEL_CRITICAL));
        try
        {
            // This constructor previously dispatched native size hints before
            // m_mainWidget existed, and stored the default size as a minimum.
            frame = new wxFrame(NULL, wxID_ANY, "GTK4 creation contract");
            Check(frame->GetMinSize() == wxDefaultSize,
                  "default frame must not acquire a child minimum size");
            GtkWidget* content = gtk_window_get_child(GTK_WINDOW(frame->GetHandle()));
            Check(GTK_IS_WIDGET(content), "frame owns native content");
            int width, height;
            gtk_widget_get_size_request(content, &width, &height);
            Check(width == -1 && height == -1, "native content has no implicit minimum");

            // No mapping/decorations yet: client and top-level hints coincide.
            const wxSize minimum(120, 80);
            frame->SetMinSize(minimum);
            Check(frame->GetMinSize() == minimum, "explicit minimum is retained");
            gtk_widget_get_size_request(content, &width, &height);
            Check(width == minimum.x && height == minimum.y,
                  "explicit minimum reaches the native content");

            const long styles[] = { wxALIGN_LEFT, wxALIGN_CENTRE, wxALIGN_RIGHT };
            const float alignments[] = { 0.0f, 0.5f, 1.0f };
            for (unsigned i = 0; i < 3; ++i)
            {
                wxSpinCtrl* spin = new wxSpinCtrl(frame, wxID_ANY, "17",
                    wxDefaultPosition, wxDefaultSize, wxSP_ARROW_KEYS | styles[i],
                    -100, 100, 17);
                GtkWidget* widget = static_cast<GtkWidget*>(spin->GetHandle());
                Check(GTK_IS_SPIN_BUTTON(widget) && GTK_IS_EDITABLE(widget),
                      "spin control exposes the native editable interface");
                Check(std::fabs(gtk_editable_get_alignment(GTK_EDITABLE(widget)) -
                                alignments[i]) < 0.001f,
                      "native spin alignment matches its wx style");
                Check(spin->GetValue() == 17, "alignment preserves the initial value");
            }
            result = 0;
        }
        catch (const std::exception& error)
        {
            std::fprintf(stderr, "creation4: %s\n", error.what());
        }
        return true;
    }

    int OnRun() wxOVERRIDE
    {
        delete frame;
        frame = NULL;
        g_log_set_always_fatal(previousFatal);
        if (result == 0) std::puts("creation4 contract PASS");
        return result;
    }
};
wxIMPLEMENT_APP(CreationContract);
