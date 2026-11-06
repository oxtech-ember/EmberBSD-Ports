// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/dataview.h>
#include <wx/textctrl.h>
#include <wx/timer.h>
#include <wx/sizer.h>
#include <wx/dc.h>
#include <wx/checkbox.h>
#include <wx/dataobj.h>
#include <wx/weakref.h>
#include <memory>
#include <gtk/gtk.h>
#include <cstdio>
#include <stdexcept>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }
class CustomCell : public wxDataViewCustomRenderer
{
    wxString text;
public:
    unsigned rendered = 0;
    CustomCell() : wxDataViewCustomRenderer("string", wxDATAVIEW_CELL_EDITABLE) {}
    bool SetValue(const wxVariant& value) wxOVERRIDE { text = value.GetString(); return true; }
    bool GetValue(wxVariant& value) const wxOVERRIDE { value = text; return true; }
    bool Render(wxRect area, wxDC* dc, int flags) wxOVERRIDE
    { ++rendered; RenderText(text, 0, area, dc, flags); return true; }
    wxSize GetSize() const wxOVERRIDE { return wxSize(100, 24); }
    bool HasEditorCtrl() const wxOVERRIDE { return true; }
    wxWindow* CreateEditorCtrl(wxWindow* parent, wxRect area, const wxVariant& value) wxOVERRIDE
    { return new wxTextCtrl(parent, wxID_ANY, value.GetString(), area.GetPosition(), area.GetSize()); }
    bool GetValueFromEditorCtrl(wxWindow* editor, wxVariant& value) wxOVERRIDE
    { value = static_cast<wxTextCtrl*>(editor)->GetValue(); return true; }
};
class DataViewContract : public wxApp
{
    wxFrame* frame = NULL;
    wxDataViewListCtrl* view = NULL;
    CustomCell* custom = NULL;
    wxDataViewColumn* customColumn = NULL;
    wxTimer timer;
    int result = 1;
    void Run()
    {
        timer.Stop();
        try
        {
            GtkTreeView* tree = GTK_TREE_VIEW(view->GtkGetTreeView());
            Check(GTK_IS_TREE_VIEW(tree), "native GTK tree view retained");
            auto selectionEvents = std::make_shared<unsigned>(0);
            view->Bind(wxEVT_DATAVIEW_SELECTION_CHANGED, [selectionEvents](wxDataViewEvent&) { ++*selectionEvents; });
            GtkTreePath* first = gtk_tree_path_new_from_indices(0, -1);
            gtk_tree_selection_select_path(gtk_tree_view_get_selection(tree), first);
            Check(*selectionEvents == 1 && view->GetSelectedRow() == 0, "native selection updates wx once");
            GtkCellRenderer* text = view->GetColumn(0)->GetRenderer()->GetGtkHandle();
            g_signal_emit_by_name(text, "edited", "0", "edited");
            Check(view->GetTextValue(0, 0) == "edited", "native text edit updates model");
            GtkCellRenderer* toggle = view->GetColumn(1)->GetRenderer()->GetGtkHandle();
            g_signal_emit_by_name(toggle, "toggled", "0");
            Check(view->GetToggleValue(0, 1), "native toggle updates model");
            custom->SetValue(wxVariant("custom snapshot text"));
            GtkRequisition minimum, natural;
            gtk_cell_renderer_get_preferred_size(custom->GetGtkHandle(), GTK_WIDGET(tree), &minimum, &natural);
            Check(minimum.width >= 100 && minimum.height >= 24, "custom cell uses real GTK4 measure vfuncs");
            GtkSnapshot* snapshot = gtk_snapshot_new();
            GdkRectangle area = { 0, 0, 180, 30 };
            const unsigned before = custom->rendered;
            gtk_cell_renderer_snapshot(custom->GetGtkHandle(), snapshot, GTK_WIDGET(tree), &area, &area,
                                       GTK_CELL_RENDERER_FOCUSED);
            GskRenderNode* node = gtk_snapshot_free_to_node(snapshot);
            Check(custom->rendered == before + 1 && node, "custom RenderText produces a real snapshot node");
            gsk_render_node_unref(node);
            view->EditItem(view->RowToItem(0), customColumn);
            GtkWidget* editor = custom->GtkGetEditorWidget();
            Check(editor && GTK_IS_CELL_EDITABLE(editor) && GTK_IS_BOX(editor), "custom editor has native GtkBox CellEditable wrapper");
            gboolean cancelled = FALSE;
            g_object_set(editor, "editing-canceled", TRUE, NULL);
            g_object_get(editor, "editing-canceled", &cancelled, NULL);
            Check(cancelled, "native editing-canceled property retains state");
            custom->CancelEditing();
            Check(!custom->GetEditorCtrl(), "custom editor cancellation releases wx editor");
            gtk_tree_path_free(first);
            view->GetColumn(0)->SetSortOrder(true);
            GtkTreePath* path = gtk_tree_path_new_from_indices(0, -1);
            const unsigned row = view->ItemToRow(view->GTKPathToItem(path));
            gtk_tree_path_free(path);
            Check(view->GetTextValue(row, 0) == "beta", "native sorting preserves model-item identity");
            view->DeleteItem(row);
            Check(view->GetItemCount() == 1, "model removal updates native view");
            result = 0;
            std::puts("GTK4 DataView model, editing, snapshot and selection contracts PASS");
        }
        catch (const std::exception& error)
        { std::fprintf(stderr, "FAIL: %s\n", error.what()); }
        frame->Destroy();
    }
public:
    bool OnInit() wxOVERRIDE
    {
        if (argc > 1 && wxString(argv[1]) == "interactive") return Interactive();
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 DataView contract", wxDefaultPosition, wxSize(700, 300));
        view = new wxDataViewListCtrl(frame, wxID_ANY, wxDefaultPosition, wxDefaultSize, wxDV_ROW_LINES);
        view->AppendTextColumn("Text", wxDATAVIEW_CELL_EDITABLE, 180, wxALIGN_LEFT, wxDATAVIEW_COL_SORTABLE);
        view->AppendToggleColumn("Toggle", wxDATAVIEW_CELL_ACTIVATABLE, 100);
        custom = new CustomCell;
        customColumn = new wxDataViewColumn("Custom", custom, 2, 240);
        view->AppendColumn(customColumn, "string");
        wxVector<wxVariant> row;
        row.push_back(wxVariant("alpha")); row.push_back(wxVariant(false)); row.push_back(wxVariant("custom"));
        view->AppendItem(row);
        row[0] = "beta"; view->AppendItem(row);
        auto sizer = new wxBoxSizer(wxVERTICAL); sizer->Add(view, 1, wxEXPAND); frame->SetSizer(sizer);
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Run(); });
        frame->Show(); timer.StartOnce(400);
        return true;
    }
    bool Interactive()
    {
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 DataView native row drag contract", wxDefaultPosition, wxSize(700, 450));
        frame->CreateStatusBar();
        auto tree = new wxDataViewTreeCtrl(frame, wxID_ANY);
        auto veto = new wxCheckBox(frame, wxID_ANY, "Veto drops (drag onto collapsed folders; hover and scroll near edges)");
        auto destroy = new wxCheckBox(frame, wxID_ANY, "Destroy tree during DROP_POSSIBLE");
        auto replace = new wxCheckBox(frame, wxID_ANY, "Replace target once during DROP_POSSIBLE");
        auto box = new wxBoxSizer(wxVERTICAL);
        box->Add(replace, 0, wxALL, 8);
        box->Add(veto, 0, wxALL, 8); box->Add(destroy, 0, wxALL, 8); box->Add(tree, 1, wxEXPAND);
        frame->SetSizer(box);
        for (int i = 0; i != 40; ++i)
        {
            auto folder = tree->AppendContainer(wxDataViewItem(), wxString::Format("Folder %02d", i));
            for (int j = 0; j != 3; ++j) tree->AppendItem(folder, wxString::Format("Item %d", j));
        }
        tree->EnableDragSource(wxDataFormat(wxDF_UNICODETEXT));
        tree->EnableDropTarget(wxDataFormat(wxDF_UNICODETEXT));
        wxWeakRef<wxDataViewTreeCtrl> alive(tree);
        wxWeakRef<wxFrame> window(frame);
        tree->Bind(wxEVT_DATAVIEW_ITEM_BEGIN_DRAG, [alive](wxDataViewEvent& event)
        { if (alive) { event.SetDataObject(new wxTextDataObject(alive->GetItemText(event.GetItem()))); event.Allow(); } });
        tree->Bind(wxEVT_DATAVIEW_ITEM_DROP_POSSIBLE, [alive, window, veto, destroy, replace](wxDataViewEvent& event)
        {
            if (window) window->SetStatusText(wxString::Format("DROP_POSSIBLE: %zu bytes", event.GetDataSize()));
            if (replace->GetValue())
            {
                replace->SetValue(false);
                if (alive) alive->EnableDropTarget(wxDataFormat(wxDF_UNICODETEXT));
                event.Veto(); return;
            }
            if (destroy->GetValue())
            {
                if (alive) alive->Destroy();
                event.Veto(); return;
            }
            if (veto->GetValue()) event.Veto(); else event.Allow();
        });
        tree->Bind(wxEVT_DATAVIEW_ITEM_DROP, [window](wxDataViewEvent& event)
        {
            const wxString value = wxString::FromUTF8(static_cast<const char*>(event.GetDataBuffer()), event.GetDataSize());
            if (window) window->SetStatusText("DROP: " + value);
            std::printf("DataView DROP: %s\n", static_cast<const char*>(value.utf8_str()));
            event.Allow();
        });
        result = 0; // Interactive observations, not an automatic acceptance test.
        frame->Show();
        return true;
    }
    int OnExit() wxOVERRIDE { return result; }
};
wxIMPLEMENT_APP(DataViewContract);
