// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/toolbar.h>
#include <wx/button.h>
#include <wx/image.h>
#include <wx/timer.h>
#include <wx/log.h>
#include <wx/weakref.h>
#include <gtk/gtk.h>
#include <cstdio>
#include <stdexcept>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }
class ContractBar : public wxToolBar
{
public:
    bool veto = false;
    ContractBar(wxWindow* parent) : wxToolBar(parent, wxID_ANY, wxDefaultPosition,
        wxSize(250, 75), wxTB_HORIZONTAL | wxTB_TEXT | wxTB_NOICONS) {}
    bool OnLeftClick(int id, bool down) wxOVERRIDE
    { return veto ? false : wxToolBar::OnLeftClick(id, down); }
    GtkWidget* Item(unsigned pos)
    {
        GtkWidget* child = gtk_widget_get_first_child(GTK_WIDGET(GTKGetToolbar()));
        while (child && pos--) child = gtk_widget_get_next_sibling(child);
        Check(child != NULL, "native toolbar item exists");
        return child;
    }
};
class ToolbarContract : public wxApp
{
    wxFrame* frame = NULL;
    ContractBar* bar = NULL;
    wxButton* control = NULL;
    wxTimer timer;
    int result = 1;
    void Run()
    {
        timer.Stop();
        try
        {
            int commands = 0, dropdowns = 0;
            bar->Bind(wxEVT_TOOL, [&](wxCommandEvent&) { ++commands; });
            bar->Bind(wxEVT_TOOL_DROPDOWN, [&](wxCommandEvent&) { ++dropdowns; });
            Check(bar->GetToolState(1003) && !bar->GetToolState(1004) && bar->GetToolState(1005),
                  "each initial contiguous radio group has one active tool");
            g_signal_emit_by_name(bar->Item(0), "clicked");
            Check(commands == 1, "normal button sends one wx command");
            gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(bar->Item(1)), TRUE);
            Check(bar->GetToolState(1002) && commands == 2, "native check changes wx state and emits command");
            bar->veto = true;
            gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(bar->Item(1)), FALSE);
            Check(bar->GetToolState(1002) && gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(bar->Item(1))),
                  "check veto restores both states");
            bar->veto = false;
            gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(bar->Item(3)), TRUE);
            Check(!bar->GetToolState(1003) && bar->GetToolState(1004), "native radio updates contiguous wx group");
            bar->veto = true;
            gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(bar->Item(2)), TRUE);
            Check(!bar->GetToolState(1003) && bar->GetToolState(1004), "radio veto restores previous selected tool");
            bar->veto = false;
            Check(bar->DeleteToolByPos(4), "separator removed");
            Check(bar->GetToolState(1004) && !bar->GetToolState(1005), "removing separator merges radio groups");
            bar->EnableTool(1002, false);
            const int before = commands;
            gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(bar->Item(1)), FALSE);
            Check(bar->GetToolState(1002) && commands == before && !gtk_widget_get_sensitive(bar->Item(1)),
                  "disabled tool cannot change logical state or emit command");
            bar->EnableTool(1002, true);
            bar->FindById(1001)->SetLabel("Updated");
            GtkWidget* label = gtk_widget_get_last_child(gtk_button_get_child(GTK_BUTTON(bar->Item(0))));
            Check(gtk_label_get_text(GTK_LABEL(label)) == wxString("Updated"), "dynamic label reaches real GtkLabel");
            bar->SetToolShortHelp(1001, "Updated help");
            Check(wxString::FromUTF8(gtk_widget_get_tooltip_text(bar->Item(0))) == "Updated help", "dynamic tooltip retained");
            wxToolBarToolBase* removed = bar->RemoveTool(1002);
            Check(removed && bar->InsertTool(1, removed), "removed button can be reinserted with its state");
            Check(gtk_toggle_button_get_active(GTK_TOGGLE_BUTTON(bar->Item(1))), "reinserted check has native state");
            wxWeakRef<wxButton> weakControl(control);
            removed = bar->RemoveTool(control->GetId());
            Check(removed && weakControl && bar->InsertTool(bar->GetToolsCount(), removed), "control survives remove/reinsert");
            Check(gtk_widget_get_parent(control->GetHandle()) == bar->GTKGetToolbar(), "control returns to native toolbar box");
            bar->SetToggle(1001, true);
            Check(GTK_IS_TOGGLE_BUTTON(bar->Item(0)), "dynamic toggle rebuilds native button");
            bar->SetToggle(1001, false);
            Check(GTK_IS_BUTTON(bar->Item(0)) && !GTK_IS_TOGGLE_BUTTON(bar->Item(0)), "dynamic normal button restored");
            GtkWidget* arrow = gtk_widget_get_last_child(bar->Item(5));
            g_signal_emit_by_name(arrow, "clicked");
            Check(dropdowns == 1, "split arrow dispatches wx dropdown event");
            bar->SetWindowStyleFlag(wxTB_HORIZONTAL | wxTB_TEXT);
            GtkWidget* image = gtk_widget_get_first_child(gtk_button_get_child(GTK_BUTTON(bar->Item(0))));
            int minimum = 0, natural = 0;
            gtk_widget_measure(image, GTK_ORIENTATION_HORIZONTAL, -1, &minimum, &natural, NULL, NULL);
            Check(gtk_widget_get_visible(image) && minimum > 0 && natural > 0,
                  "switching from text-only restores real bitmap dimensions");
            bar->EnableTool(1001, false);
            gtk_widget_measure(image, GTK_ORIENTATION_HORIZONTAL, -1, &minimum, &natural, NULL, NULL);
            Check(minimum > 0, "generated disabled bitmap retains dimensions");
            GtkWidget* viewport = gtk_scrolled_window_get_child(GTK_SCROLLED_WINDOW(bar->GetHandle()));
            Check(GTK_IS_VIEWPORT(viewport) && gtk_viewport_get_scroll_to_focus(GTK_VIEWPORT(viewport)),
                  "overflow viewport keeps keyboard focus visible");
            bar->SetWindowStyleFlag(wxTB_VERTICAL | wxTB_TEXT | wxTB_NOICONS);
            Check(gtk_orientable_get_orientation(GTK_ORIENTABLE(bar->GTKGetToolbar())) == GTK_ORIENTATION_VERTICAL,
                  "dynamic toolbar orientation reaches GTK layout");
            ContractBar* deleting = new ContractBar(frame);
            deleting->AddCheckTool(2001, "Delete toolbar", wxNullBitmap);
            deleting->Realize();
            wxWeakRef<ContractBar> weak(deleting);
            GtkWidget* native = GTK_WIDGET(g_object_ref(deleting->Item(0)));
            deleting->Bind(wxEVT_TOOL, [deleting](wxCommandEvent&) { delete deleting; });
            gtk_toggle_button_set_active(GTK_TOGGLE_BUTTON(native), TRUE);
            Check(!weak, "toolbar destruction in command callback returns safely");
            g_object_unref(native);
            delete bar; bar = NULL;
            result = 0;
            std::puts("GTK4 toolbar state, regrouping, mutation and lifetime contracts PASS");
        }
        catch (const std::exception& error)
        { std::fprintf(stderr, "FAIL: %s\n", error.what()); }
        if (bar) { delete bar; bar = NULL; }
        frame->Destroy();
    }
public:
    bool OnInit() wxOVERRIDE
    {
        wxLog::SetActiveTarget(new wxLogStderr);
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 toolbar contract", wxDefaultPosition, wxSize(480, 220));
        bar = new ContractBar(frame);
        wxImage image(16, 16);
        image.SetRGB(wxRect(0, 0, 16, 16), 20, 110, 210);
        bar->AddTool(1001, "Normal", wxBitmap(image));
        bar->AddCheckTool(1002, "Check", wxNullBitmap);
        bar->AddRadioTool(1003, "Radio 1", wxNullBitmap);
        bar->AddRadioTool(1004, "Radio 2", wxNullBitmap);
        bar->AddSeparator();
        bar->AddRadioTool(1005, "Radio 3", wxNullBitmap);
        bar->AddTool(1006, "Dropdown", wxNullBitmap, wxEmptyString, wxITEM_DROPDOWN);
        control = new wxButton(bar, wxID_ANY, "Embedded control");
        bar->AddControl(control);
        bar->Realize();
        frame->Show();
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Run(); });
        timer.StartOnce(300);
        return true;
    }
    int OnRun() wxOVERRIDE { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(ToolbarContract);
