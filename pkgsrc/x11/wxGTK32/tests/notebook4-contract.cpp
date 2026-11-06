// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/panel.h>
#include <wx/button.h>
#include <wx/checkbox.h>
#include <wx/timer.h>
#include <wx/log.h>
#include <wx/notebook.h>
#include <wx/statbox.h>
#include <wx/weakref.h>
#include <gtk/gtk.h>
#include <cstdio>
#include <stdexcept>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }
class NotebookContract : public wxApp
{
    wxFrame* frame = NULL;
    wxNotebook* book = NULL;
    wxStaticBox* box = NULL;
    wxCheckBox* label = NULL;
    wxTimer timer;
    int result = 1;
    void Run()
    {
        timer.Stop();
        try
        {
            int changed = 0;
            bool veto = true, nested = false, remove = false;
            wxWindow* last = book->GetPage(2);
            book->Bind(wxEVT_NOTEBOOK_PAGE_CHANGING, [&](wxBookCtrlEvent& event)
            {
                if (veto) event.Veto();
                else if (nested)
                {
                    nested = false;
                    book->ChangeSelection(2);
                }
                else if (remove)
                {
                    remove = false;
                    book->DeletePage(event.GetSelection());
                }
            });
            book->Bind(wxEVT_NOTEBOOK_PAGE_CHANGED, [&](wxBookCtrlEvent&) { ++changed; });
            GtkNotebook* native = GTK_NOTEBOOK(book->GetHandle());
            gtk_notebook_set_current_page(native, 1);
            Check(book->GetSelection() == 0 && changed == 0, "native page selection veto precedes GTK class handler");
            veto = false;
            gtk_notebook_set_current_page(native, 1);
            Check(book->GetSelection() == 1 && changed == 1, "allowed native selection sends one changed event");
            nested = true;
            gtk_notebook_set_current_page(native, 0);
            Check(book->GetSelection() == 2 && changed == 1, "nested silent selection supersedes outer request");
            remove = true;
            gtk_notebook_set_current_page(native, 1);
            Check(book->GetPageCount() == 2 && book->GetCurrentPage() == last,
                  "deleting requested page during changing preserves current page identity");
            veto = true;
            Check(!book->RemovePage(book->GetSelection()) && book->GetPageCount() == 2,
                  "selected-page removal veto leaves native and wx page lists intact");
            veto = false;
            const bool removed = book->RemovePage(book->GetSelection());
            Check(removed && book->GetPageCount() == 1 &&
                  gtk_notebook_get_n_pages(native) == 1, "page removal synchronizes native and wx lists");
            delete last;
            book->SetPageText(0, "Changed label");
            book->SetPadding(wxSize(6, 4));
            book->SetTabSize(wxSize(30, 90));
            Check(book->GetPageText(0) == "Changed label", "dynamic label retained");
            GtkWidget* tab = gtk_notebook_get_tab_label(native, GTK_WIDGET(book->GetPage(0)->GetHandle()));
            int width = 0, height = 0;
            gtk_widget_get_size_request(tab, &width, &height);
            Check(width == 30 && height == 90, "native tab size request retained");
            Check(label->GetParent() == box && gtk_frame_get_label_widget(GTK_FRAME(box->GetHandle())) == label->GetHandle(),
                  "static-box label window transfers wx and GTK ownership");
            Check(gtk_frame_get_child(GTK_FRAME(box->GetHandle())) == box->m_wxwindow,
                  "static-box content uses GtkFrame child API");
            int top, other;
            box->GetBordersForSizer(&top, &other);
            Check(top > 0 && other >= 0, "static-box metrics use actual label and frame style");
            wxNotebook* deleting = new wxNotebook(frame, wxID_ANY);
            deleting->AddPage(new wxPanel(deleting), "one");
            deleting->AddPage(new wxPanel(deleting), "two");
            wxWeakRef<wxNotebook> weak(deleting);
            GtkNotebook* deletionNative = GTK_NOTEBOOK(g_object_ref(deleting->GetHandle()));
            deleting->Bind(wxEVT_NOTEBOOK_PAGE_CHANGING, [deleting](wxBookCtrlEvent&) { delete deleting; });
            gtk_notebook_set_current_page(deletionNative, 1);
            Check(!weak, "notebook destruction during native changing callback returns safely");
            g_object_unref(deletionNative);
            // Remove handlers whose captures are local before normal teardown.
            delete book;
            book = NULL;
            result = 0;
            std::puts("GTK4 notebook veto, mutation, lifetime and static-box contracts PASS");
        }
        catch (const std::exception& e) { std::fprintf(stderr, "%s\n", e.what()); }
        frame->Destroy();
        ExitMainLoop();
    }
public:
    bool OnInit() override
    {
        wxLog::SetActiveTarget(new wxLogStderr);
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 notebook/static-box contract", wxDefaultPosition, wxSize(640, 480));
        book = new wxNotebook(frame, wxID_ANY, wxPoint(10, 10), wxSize(320, 400), wxNB_RIGHT);
        for (int i = 0; i < 3; ++i) book->AddPage(new wxPanel(book), wxString::Format("Page %d", i));
        label = new wxCheckBox(frame, wxID_ANY, "Enabled group");
        box = new wxStaticBox(frame, wxID_ANY, label, wxPoint(350, 10), wxSize(240, 180));
        new wxButton(box, wxID_ANY, "Child", wxPoint(20, 40));
        frame->Show();
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Run(); });
        timer.StartOnce(500);
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(NotebookContract);
