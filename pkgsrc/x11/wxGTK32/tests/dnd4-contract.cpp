// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Interactive fixture: all drag events come from the display server.
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/panel.h>
#include <wx/sizer.h>
#include <wx/stattext.h>
#include <wx/choice.h>
#include <wx/dnd.h>
#include <wx/dataobj.h>
#include <wx/weakref.h>
#include <cstdio>
#include <memory>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
struct Results
{
    wxWeakRef<wxFrame> frame;
    wxWeakRef<wxPanel> target;
    wxWeakRef<wxChoice> mode;
    unsigned entered = 0, received = 0, copied = 0, moved = 0, cancelled = 0;
    void Report(const wxString& message)
    {
        std::printf("%s\n", static_cast<const char*>(message.utf8_str()));
        std::fflush(stdout);
        if (frame) frame->SetStatusText(message);
    }
};
class Target : public wxDropTarget
{
    std::shared_ptr<Results> state;
public:
    explicit Target(const std::shared_ptr<Results>& value)
        : wxDropTarget(new wxTextDataObject), state(value) {}
    wxDragResult OnEnter(wxCoord, wxCoord, wxDragResult suggested) wxOVERRIDE
    {
        auto value = state;
        ++value->entered;
        if (value->mode && value->mode->GetSelection() == 2)
        {
            value->Report("Removing target inside OnEnter; drag must cancel safely");
            value->target->SetDropTarget(NULL); // Deletes this; no later owner access.
            return wxDragNone;
        }
        return suggested;
    }
    bool OnDrop(wxCoord, wxCoord) wxOVERRIDE
    {
        if (state->mode && state->mode->GetSelection() == 1)
        { state->Report("Drop vetoed; source must not report copy or move"); return false; }
        return true;
    }
    wxDragResult OnData(wxCoord, wxCoord, wxDragResult suggested) wxOVERRIDE
    {
        auto value = state;
        if (!GetData() || !value->target || value->target->GetDropTarget() != this)
        { value->Report("Read failed or cancelled"); return wxDragNone; }
        const wxString text = static_cast<wxTextDataObject*>(GetDataObject())->GetText();
        ++value->received;
        value->Report("Received: " + text);
        if (value->mode && value->mode->GetSelection() == 3)
        {
            value->target->SetDropTarget(NULL); // Deletes this after a real transfer.
            return wxDragNone;
        }
        return suggested;
    }
};
class DndContract : public wxApp
{
public:
    bool OnInit() wxOVERRIDE
    {
        auto state = std::make_shared<Results>();
        auto frame = new wxFrame(NULL, wxID_ANY, "GTK4 native DnD contract", wxDefaultPosition, wxSize(760, 420));
        state->frame = frame;
        frame->CreateStatusBar();
        auto box = new wxBoxSizer(wxVERTICAL);
        frame->SetSizer(box);
        auto instructions = new wxStaticText(frame, wxID_ANY,
            "Drag the source onto the target. Ctrl: copy; Shift: move; Escape: cancel.\n"
            "Try veto and target removal modes, external UTF-8 text, and close during drag.\n"
            "This fixture reports observations; it does not certify GUI acceptance automatically.");
        box->Add(instructions, 0, wxALL, 12);
        const wxString choices[] = { "Accept", "Veto drop", "Remove target on enter", "Remove target after data" };
        auto mode = new wxChoice(frame, wxID_ANY, wxDefaultPosition, wxDefaultSize, 4, choices);
        mode->SetSelection(0); state->mode = mode;
        box->Add(mode, 0, wxALL, 12);
        auto row = new wxBoxSizer(wxHORIZONTAL);
        box->Add(row, 1, wxEXPAND | wxALL, 12);
        auto source = new wxPanel(frame, wxID_ANY);
        source->SetBackgroundColour(wxColour(160, 190, 220));
        auto target = new wxPanel(frame, wxID_ANY);
        state->target = target;
        target->SetBackgroundColour(wxColour(190, 220, 160));
        new wxStaticText(source, wxID_ANY, "Drag source", wxPoint(15, 15));
        new wxStaticText(target, wxID_ANY, "Drop target", wxPoint(15, 15));
        row->Add(source, 1, wxEXPAND | wxRIGHT, 12);
        row->Add(target, 1, wxEXPAND);
        target->SetDropTarget(new Target(state));
        mode->Bind(wxEVT_CHOICE, [state](wxCommandEvent&)
        { if (state->target) state->target->SetDropTarget(new Target(state)); });
        source->Bind(wxEVT_MOTION, [state, source](wxMouseEvent& event)
        {
            auto value = state; // The native nested loop may destroy the source/handler.
            if (!event.Dragging() || !event.LeftIsDown()) { event.Skip(); return; }
            wxTextDataObject payload(wxString::FromUTF8("native DnD — Ελληνικά — 日本語"));
            wxDropSource drag(payload, source);
            const wxDragResult result = drag.DoDragDrop(wxDrag_AllowMove);
            if (result == wxDragCopy) ++value->copied;
            else if (result == wxDragMove) ++value->moved;
            else ++value->cancelled;
            value->Report(wxString::Format("result=%d enter=%u data=%u copy=%u move=%u cancel/none=%u",
                int(result), value->entered, value->received, value->copied, value->moved, value->cancelled));
        });
        frame->Show();
        return true;
    }
};
wxIMPLEMENT_APP(DndContract);
