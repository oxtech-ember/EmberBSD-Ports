// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/filectrl.h>
#include <wx/filedlg.h>
#include <wx/dirdlg.h>
#include <wx/filepicker.h>
#include <wx/filename.h>
#include <wx/file.h>
#include <wx/panel.h>
#include <wx/checkbox.h>
#include <wx/timer.h>
#include <wx/weakref.h>
#include <gtk/gtk.h>
#include <chrono>
#include <cstdio>
#include <functional>
#include <stdexcept>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }
static bool Property(GObject* object, const char* name)
{
    Check(g_object_class_find_property(G_OBJECT_GET_CLASS(object), name) != NULL,
          "shared GTK chooser property is present");
    gboolean value = FALSE;
    g_object_get(object, name, &value, NULL);
    return value != FALSE;
}
static bool DesktopHidden()
{
    GSettings* settings = g_settings_new("org.gtk.gtk4.Settings.FileChooser");
    bool value = g_settings_get_boolean(settings, "show-hidden") != FALSE;
    g_object_unref(settings);
    return value;
}
static void Wait(const std::function<bool()>& ready)
{
    const auto end = std::chrono::steady_clock::now() + std::chrono::seconds(8);
    while (!ready() && std::chrono::steady_clock::now() < end)
    {
        wxYield();
        g_usleep(1000);
    }
    Check(ready(), "asynchronous chooser operation completed");
}
// Exercise the real GtkFileChooserDialog response validation, including its
// asynchronous file query and native overwrite confirmation, without private APIs.
static void AcceptExisting(wxFileDialog& dialog, bool expectPrompt)
{
    wxTimer driver;
    bool requested = false, sawPrompt = false, expired = false;
    int ticks = 0;
    driver.Bind(wxEVT_TIMER, [&](wxTimerEvent&)
    {
        if (!requested)
        {
            requested = true;
            gtk_dialog_response(GTK_DIALOG(dialog.GetHandle()), GTK_RESPONSE_ACCEPT);
            return;
        }
        GListModel* windows = gtk_window_get_toplevels();
        for (guint i = 0; i < g_list_model_get_n_items(windows); ++i)
        {
            GtkWindow* window = GTK_WINDOW(g_list_model_get_item(windows, i));
            if (gtk_window_get_transient_for(window) == GTK_WINDOW(dialog.GetHandle()) &&
                gtk_widget_get_visible(GTK_WIDGET(window)))
            {
                sawPrompt = true;
                if (GTK_IS_DIALOG(window)) gtk_dialog_response(GTK_DIALOG(window), GTK_RESPONSE_CANCEL);
                else gtk_window_close(window);
                g_object_unref(window);
                dialog.EndModal(wxID_CANCEL);
                return;
            }
            g_object_unref(window);
        }
        if (++ticks >= 80)
        {
            expired = true;
            dialog.EndModal(wxID_CANCEL);
        }
    });
    driver.Start(100);
    const int result = dialog.ShowModal();
    driver.Stop();
    Check(!expired && sawPrompt == expectPrompt, "native overwrite policy controls confirmation");
    Check(result == (expectPrompt ? wxID_CANCEL : wxID_OK), "native save response matches policy");
}
class FileChooserContract : public wxApp
{
    wxFrame* frame = NULL;
    wxString path;
    int result = 1;
    bool interactive = false;
    void Run()
    {
        try
        {
            path = wxFileName::CreateTempFileName("wx-chooser4-");
            Check(!path.empty(), "temporary local file created");
            const wxString directory = wxFileName(path).GetPath();
            wxFileDialog open(frame, "Open", directory, "", "All|*|Text|*.txt",
                              wxFD_OPEN | wxFD_MULTIPLE | wxFD_SHOW_HIDDEN);
            GObject* native = G_OBJECT(open.GetHandle());
            Check(Property(native, "show-hidden"), "dialog hidden-file policy");
            Check(Property(native, "do-overwrite-confirmation"), "GTK default overwrite policy retained");
            open.SetFilterIndex(1);
            Check(open.GetFilterIndex() == 1, "filter index tracks GListModel");
            open.SetWildcard("Only files|*");
            Check(open.GetFilterIndex() == 0, "filter replacement resets selection");
            GListModel* filters = gtk_file_chooser_get_filters(GTK_FILE_CHOOSER(native));
            Check(g_list_model_get_n_items(filters) == 1, "replacing filters releases old list");
            g_object_unref(filters);

            wxFileDialog save(frame, "Save", directory, wxFileName(path).GetFullName(),
                              "All|*", wxFD_SAVE);
            Check(!Property(G_OBJECT(save.GetHandle()), "do-overwrite-confirmation"),
                  "save without wxFD_OVERWRITE_PROMPT bypasses GTK prompt");
            wxFileDialog prompt(frame, "Confirm overwrite", directory,
                                wxFileName(path).GetFullName(), "All|*",
                                wxFD_SAVE | wxFD_OVERWRITE_PROMPT | wxFD_PREVIEW);
            Check(Property(G_OBJECT(prompt.GetHandle()), "do-overwrite-confirmation"),
                  "save overwrite flag selects native confirmation");

            prompt.SetExtraControlCreator(+[](wxWindow* parent) -> wxWindow*
            { return new wxCheckBox(parent, wxID_ANY, "Native dialog extra control"); });
            Wait([&] { return save.GetPath() == path && prompt.GetPath() == path; });
            AcceptExisting(save, false);
            AcceptExisting(prompt, true);
            Check(prompt.GetExtraControl() != NULL, "native chooser hosts extra control");
            const bool desktopHidden = DesktopHidden();
            auto* ctrl = new wxFileCtrl(frame, wxID_ANY, directory, "", "All|*",
                                        wxFC_OPEN, wxDefaultPosition, wxSize(640, 400));
            int selections = 0;
            ctrl->Bind(wxEVT_FILECTRL_SELECTIONCHANGED,
                       [&](wxFileCtrlEvent&) { ++selections; });
            ctrl->ShowHidden(!desktopHidden);
            Check(Property(G_OBJECT(ctrl->GetHandle()), "show-hidden") == !desktopHidden, "embedded chooser hidden files");
            ctrl->Hide(); ctrl->Show();
            Check(Property(G_OBJECT(ctrl->GetHandle()), "show-hidden") == !desktopHidden, "explicit hidden setting survives remap");
            ctrl->SetPath(path);
            Wait([&] { return selections > 0 && ctrl->GetPath() == path; });
            wxArrayString selected;
            ctrl->GetPaths(selected);
            Check(selected.size() == 1 && selected[0] == path, "GFile paths retain selected local file");
            delete ctrl;
            Check(DesktopHidden() == desktopHidden, "explicit chooser state does not change desktop preference");

            // Destroy a native chooser during its coalesced selection callback.
            GtkWidget* dying = gtk_file_chooser_widget_new(GTK_FILE_CHOOSER_ACTION_SAVE);
            g_object_ref_sink(dying);
            bool delivered = false;
            gpointer weak = dying;
            g_object_add_weak_pointer(G_OBJECT(dying), &weak);
            g_signal_connect(dying, "selection-changed", G_CALLBACK(+[](GtkWidget* widget, gpointer data)
            {
                *static_cast<bool*>(data) = true;
                g_object_unref(widget);
            }), &delivered);
            gtk_file_chooser_set_current_name(GTK_FILE_CHOOSER(dying), "changed.txt");
            Check(!delivered, "selection callback waits until native mutation has unwound");
            Wait([&] { return delivered && weak == NULL; });

            // A pending callback must not retain or access a disposed chooser.
            GtkWidget* cancelled = gtk_file_chooser_widget_new(GTK_FILE_CHOOSER_ACTION_SAVE);
            g_object_ref_sink(cancelled);
            bool unexpected = false;
            g_signal_connect(cancelled, "selection-changed", G_CALLBACK(+[](GtkWidget*, gpointer data)
            { *static_cast<bool*>(data) = true; }), &unexpected);
            gtk_file_chooser_set_current_name(GTK_FILE_CHOOSER(cancelled), "cancelled.txt");
            g_object_unref(cancelled);
            wxYield();
            Check(!unexpected, "chooser disposal cancels pending selection notification");

            auto* fileButton = new wxFileButton(frame, wxID_ANY, "Browse", path);
            Check(GTK_IS_BUTTON(fileButton->GetHandle()), "GTK4 file picker is a native button");
            Check(fileButton->GetLabel() == wxFileName(path).GetFullName(), "picker displays selected basename");
            auto* dirButton = new wxDirButton(frame, wxID_ANY, "Browse", directory);
            Check(!(dirButton->GetDialogStyle() & wxDD_DIR_MUST_EXIST), "directory creation remains selectable");
            delete fileButton;
            delete dirButton;

            auto* owner = new wxFrame(frame, wxID_ANY, "Modal lifetime");
            auto* button = new wxFileButton(owner, wxID_ANY, "Open", path);
            wxWeakRef<wxFileButton> weakButton(button);
            wxWeakRef<wxFrame> weakOwner(owner);
            owner->Show();
            CallAfter([weakOwner]() mutable { if (weakOwner) delete weakOwner.get(); });
            wxCommandEvent click(wxEVT_BUTTON, button->GetId());
            button->OnButtonClick(click);
            Check(!weakButton && !weakOwner, "parent destruction safely unwinds picker modal loop");

            if (interactive)
            {
                std::puts("Interactive: preview an image; save over the temporary file with and without overwrite prompt; cancel each dialog. Observe extra controls and directory creation.");
                prompt.ShowModal();
                save.ShowModal();
                wxDirDialog dirs(frame, "Select or create a directory", directory, wxDD_DEFAULT_STYLE);
                dirs.ShowModal();
                std::puts("Interactive observations completed; no automatic GUI acceptance is claimed.");
            }
            result = 0;
            std::puts("GTK4 chooser automatic properties, filters, selection and lifetime contracts PASS");
        }
        catch (const std::exception& e) { std::fprintf(stderr, "%s\n", e.what()); }
        if (!path.empty()) wxRemoveFile(path);
        frame->Destroy();
        ExitMainLoop();
    }
public:
    bool OnInit() override
    {
        interactive = argc > 1 && wxString(argv[1]) == "interactive";
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 chooser contract", wxDefaultPosition, wxSize(680, 460));
        frame->Show();
        CallAfter([this] { Run(); });
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(FileChooserContract);
