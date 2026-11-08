// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/apptrait.h>
#include <wx/frame.h>
#include <wx/msgdlg.h>
#include <wx/printdlg.h>
#include <wx/timer.h>
#include <wx/weakref.h>
#include <wx/evtloop.h>
#include <gtk/gtk.h>
#include <gtk/gtkunixprint.h>
#include <cstdio>
#include <functional>
#include <stdexcept>
#if !defined(__WXGTK4__) || !wxUSE_GTKPRINT
#error This fixture requires GTK4 and real configured GTK printing support.
#endif
static void Check(bool ok, const char* why)
{ if (!ok) throw std::runtime_error(why); }
static GtkWindow* Find(GType type)
{
    GListModel* windows = gtk_window_get_toplevels();
    for (guint i = 0; i < g_list_model_get_n_items(windows); ++i)
    {
        GObject* item = G_OBJECT(g_list_model_get_item(windows, i));
        if (G_TYPE_CHECK_INSTANCE_TYPE(item, type)) return GTK_WINDOW(item);
        g_object_unref(item);
    }
    return NULL;
}
static GtkWidget* Child(GtkWidget* root, GType type, const char* label = NULL)
{
    if (G_TYPE_CHECK_INSTANCE_TYPE(root, type) &&
        (!label || (GTK_IS_BUTTON(root) && g_strcmp0(gtk_button_get_label(GTK_BUTTON(root)), label) == 0)))
        return root;
    for (GtkWidget* child = gtk_widget_get_first_child(root); child;
         child = gtk_widget_get_next_sibling(child))
        if (GtkWidget* found = Child(child, type, label)) return found;
    return NULL;
}
class ModalContract : public wxApp
{
    wxFrame* frame = NULL;
    int status = 1;
    std::function<void()> entering;
    void Message(gint nativeResponse, int expected)
    {
        wxMessageDialog dialog(frame, "Message text", "Modal contract",
                               wxYES_NO | wxCANCEL | wxHELP);
        dialog.SetYesNoLabels("&Accept", "&Reject");
        entering = [nativeResponse]
        {
            GtkWindow* native = Find(GTK_TYPE_MESSAGE_DIALOG);
            Check(native != NULL, "native message exists before loop enters");
            GtkWidget* yes = gtk_dialog_get_widget_for_response(GTK_DIALOG(native), GTK_RESPONSE_YES);
            Check(yes && g_strcmp0(gtk_button_get_label(GTK_BUTTON(yes)), "_Accept") == 0,
                  "custom message labels retained");
            if (nativeResponse == GTK_RESPONSE_DELETE_EVENT) gtk_window_close(native);
            else if (nativeResponse == GTK_RESPONSE_NONE) gtk_window_destroy(native);
            else gtk_dialog_response(GTK_DIALOG(native), nativeResponse);
            g_object_unref(native);
        };
        Check(dialog.ShowModal() == expected, "message response and pre-loop cancellation mapping");
    }
    void Run()
    {
        try
        {
            Message(GTK_RESPONSE_YES, wxID_YES);
            Message(GTK_RESPONSE_NO, wxID_NO);
            Message(GTK_RESPONSE_HELP, wxID_HELP);
            Message(GTK_RESPONSE_CANCEL, wxID_CANCEL);
            Message(GTK_RESPONSE_DELETE_EVENT, wxID_CANCEL);
            Message(GTK_RESPONSE_NONE, wxID_CANCEL);

            wxMessageDialog outer(frame, "Outer", "Nested modal", wxYES_NO);
            entering = [&]
            {
                GtkWindow* native = Find(GTK_TYPE_MESSAGE_DIALOG);
                wxMessageDialog inner(frame, "Inner", "Nested modal", wxOK);
                entering = [native]
                {
                    gtk_dialog_response(GTK_DIALOG(native), GTK_RESPONSE_YES);
                    GListModel* windows = gtk_window_get_toplevels();
                    for (guint i = 0; i < g_list_model_get_n_items(windows); ++i)
                    {
                        GObject* item = G_OBJECT(g_list_model_get_item(windows, i));
                        if (GTK_IS_MESSAGE_DIALOG(item) && item != G_OBJECT(native))
                            gtk_dialog_response(GTK_DIALOG(item), GTK_RESPONSE_OK);
                        g_object_unref(item);
                    }
                };
                Check(inner.ShowModal() == wxID_OK, "inner response unwinds its own wx loop");
                g_object_unref(native);
            };
            Check(outer.ShowModal() == wxID_YES, "outer response during nested loop is not lost");

            auto* parent = new wxFrame(frame, wxID_ANY, "Parent lifetime");
            parent->Show();
            wxMessageDialog parentDialog(parent, "Parent destruction", "Modal", wxOK);
            entering = [parent] { delete parent; };
            Check(parentDialog.ShowModal() == wxID_CANCEL, "native parent removal cancels modal wait");

            auto* formerParent = new wxFrame(frame, wxID_ANY, "Former parent");
            wxMessageDialog delayed(formerParent, "Parent removed before ShowModal", "Modal", wxOK);
            delete formerParent;
            entering = []
            {
                GtkWindow* native = Find(GTK_TYPE_MESSAGE_DIALOG);
                Check(native != NULL, "delayed native message is created");
                gtk_dialog_response(GTK_DIALOG(native), GTK_RESPONSE_OK);
                g_object_unref(native);
            };
            Check(delayed.ShowModal() == wxID_OK && delayed.GetParent() == NULL,
                  "dead parent is cleared before native message creation");

            auto* deleting = new wxMessageDialog(frame, "Owner destruction", "Modal", wxOK);
            wxWeakRef<wxMessageDialog> weak(deleting);
            entering = [deleting] { delete deleting; };
            Check(deleting->ShowModal() == wxID_CANCEL && !weak,
                  "wx owner destruction leaves no stale post-loop accesses");

            wxPageSetupDialogData settings;
            wxPageSetupDialog page(frame, &settings);
            entering = []
            {
                GtkWindow* native = Find(GTK_TYPE_PAGE_SETUP_UNIX_DIALOG);
                Check(native != NULL, "native page setup dialog exists");
                GtkPageSetup* setup = gtk_page_setup_new();
                gtk_page_setup_set_orientation(setup, GTK_PAGE_ORIENTATION_LANDSCAPE);
                gtk_page_setup_unix_dialog_set_page_setup(GTK_PAGE_SETUP_UNIX_DIALOG(native), setup);
                g_object_unref(setup);
                gtk_dialog_response(GTK_DIALOG(native), GTK_RESPONSE_OK);
                g_object_unref(native);
            };
            Check(page.ShowModal() == wxID_OK &&
                  page.GetPageSetupDialogData().GetPrintData().GetOrientation() == wxLANDSCAPE,
                  "native page setup acceptance updates print settings");
            entering = []
            {
                GtkWindow* native = Find(GTK_TYPE_PAGE_SETUP_UNIX_DIALOG);
                Check(native != NULL, "repeated page setup creates a native dialog");
                gtk_window_close(native);
                g_object_unref(native);
            };
            Check(page.ShowModal() == wxID_CANCEL, "page setup close cancels");

            // Attach before Run sets the modal property. Destruction from a
            // notify handler must not be followed by presentation of that window.
            {
            bool destroyedFromNotify = false;
            const gulong watch = g_signal_connect(gtk_window_get_toplevels(), "items-changed",
                G_CALLBACK(+[](GListModel* model, guint position, guint, guint added, gpointer data)
                {
                    for (guint i = position; i < position + added; ++i)
                    {
                        GObject* item = G_OBJECT(g_list_model_get_item(model, i));
                        if (GTK_IS_PAGE_SETUP_UNIX_DIALOG(item))
                            g_signal_connect(item, "notify::modal",
                                G_CALLBACK(+[](GObject* object, GParamSpec*, gpointer state)
                                {
                                    if (gtk_window_get_modal(GTK_WINDOW(object)))
                                    {
                                        *static_cast<bool*>(state) = true;
                                        gtk_window_destroy(GTK_WINDOW(object));
                                    }
                                }), data);
                        g_object_unref(item);
                    }
                }), &destroyedFromNotify);
            struct WatchScope
            {
                gulong handler;
                ~WatchScope() { g_signal_handler_disconnect(gtk_window_get_toplevels(), handler); }
            } scope = { watch };
            const int destroyedResult = page.ShowModal();
            Check(destroyedResult == wxID_CANCEL && destroyedFromNotify,
                  "modal notify destruction is not followed by present or a nested wait");
            }

            // GtkPrintOperation owns its native wait. A wx timer still runs in
            // that context, and cancellation does not submit a print job.
            wxTimer cancelPrint;
            cancelPrint.Bind(wxEVT_TIMER, [&](wxTimerEvent&)
            {
                if (GtkWindow* native = Find(GTK_TYPE_PRINT_UNIX_DIALOG))
                {
                    gtk_dialog_response(GTK_DIALOG(native), GTK_RESPONSE_CANCEL);
                    g_object_unref(native);
                }
            });
            cancelPrint.Start(100);
            wxPrintDialog print(frame);
            Check(print.ShowModal() == wxID_CANCEL, "native print operation cancellation");
            cancelPrint.Stop();

#if wxDEBUG_LEVEL
            entering = []
            {
                GtkWindow* native = Find(g_type_from_name("GtkAssertDialog"));
                Check(native != NULL, "native assert dialog exists");
                GtkWidget* suppress = Child(GTK_WIDGET(native), GTK_TYPE_CHECK_BUTTON);
                GtkWidget* proceed = Child(GTK_WIDGET(native), GTK_TYPE_BUTTON, "_Continue");
                Check(suppress && proceed, "assert suppression and continue controls exist");
                gtk_check_button_set_active(GTK_CHECK_BUTTON(suppress), FALSE);
                g_signal_emit_by_name(proceed, "clicked");
                g_object_unref(native);
            };
            Check(GetTraits()->ShowAssertDialog("Modal contract assertion"),
                  "assert continue-suppress result is preserved");
#endif
            status = 0;
            std::puts("GTK4 modal responses, nesting, lifetime, page setup and print cancellation PASS");
        }
        catch (const std::exception& e) { std::fprintf(stderr, "FAIL: %s\n", e.what()); }
        entering = NULL;
        frame->Destroy();
        ExitMainLoop();
    }
public:
    bool OnInit() override
    {
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 modal contract");
        frame->Show();
        CallAfter([this] { Run(); });
        return true;
    }
    void OnEventLoopEnter(wxEventLoopBase*) override
    {
        auto action = std::move(entering);
        entering = NULL;
        if (action) action();
    }
    int OnRun() override { wxApp::OnRun(); return status; }
};
wxIMPLEMENT_APP(ModalContract);
