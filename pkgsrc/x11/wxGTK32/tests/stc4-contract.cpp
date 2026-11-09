// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
// Run with the installed common wx GTK4 provider on its matching target.
#include <wx/wx.h>
#include <wx/stc/stc.h>
#include <wx/timer.h>
#include <cstdio>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires the GTK4 wx provider.
#endif

static void Check(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}

class STCContract : public wxApp
{
    wxFrame* frame = nullptr;
    wxStyledTextCtrl* editor = nullptr;
    wxTimer timer;
    int result = 1, phase = 0, ticks = 0, selections = 0, selectionChanges = 0;
    bool finished = false, selectionDataValid = true, selectionChangeValid = false;

    void Finish(int status, const char* message)
    {
        if (finished) return;
        finished = true;
        result = status;
        timer.Stop();
        std::fprintf(status ? stderr : stdout, "%s\n", message);
        frame->Destroy();
        ExitMainLoop();
    }

    void Step()
    {
        try
        {
            if (++ticks > 100) throw std::runtime_error("STC contract timed out");
            if (!editor->IsShownOnScreen()) return;
            if (phase == 0)
            {
                editor->SetText(wxString::FromUTF8("Aé😀"));
                Check(editor->GetTextLength() == 7, "UTF-8 byte length");
                Check(editor->PositionAfter(1) == 3, "UTF-8 character position");
                editor->SetSelection(1, 3);
                Check(editor->GetSelectedText() == wxString::FromUTF8("é"), "UTF-8 selection");
                editor->EmptyUndoBuffer();
                editor->ReplaceSelection("x");
                Check(editor->CanUndo(), "undo available");
                editor->Undo();
                Check(editor->GetText() == wxString::FromUTF8("Aé😀"), "undo Unicode replacement");
                editor->SetUseAntiAliasing(true);
                Check(editor->GetUseAntiAliasing(), "antialias enabled");
                editor->SetUseAntiAliasing(false);
                Check(!editor->GetUseAntiAliasing(), "antialias disabled");
                editor->SetLexer(wxSTC_LEX_PYTHON);
                Check(editor->GetLexer() == wxSTC_LEX_PYTHON, "numeric lexer API");
                editor->SetKeyWords(0, "def return");
                editor->SetText("def square(x):\n    return x*x\n");
                editor->Colourise(0, -1);
                Check(editor->GetStyleAt(0) == wxSTC_P_WORD, "shared Python lexer styles keyword");
                editor->SetLexerLanguage("cpp");
                Check(editor->GetLexerLanguage() == "cpp", "named lexer API");
                editor->SetLexer(wxSTC_LEX_CONTAINER);
                Check(editor->GetLexer() == wxSTC_LEX_CONTAINER, "container lexer ownership");
                editor->SetStyleBits(5);
                Check(editor->GetStyleBits() == 8 && editor->GetStyleBitsNeeded() == 8,
                      "modern independent style bytes");
                editor->SetText("a");
                editor->GotoPos(1);
                editor->AutoCompShow(1, "alpha beta");
                Check(editor->AutoCompActive(), "completion popup active");
                editor->AutoCompSelect("beta");
                editor->AutoCompSelect("alpha");
                Check(selectionChanges > 0 && selectionChangeValid,
                      "completion selection-change notification");
                phase = 1;
            }
            else if (phase == 1)
            {
                editor->AutoCompComplete();
                Check(editor->GetText() == "alpha" && selections == 1 && selectionDataValid,
                      "completion text and one selection notification");
                editor->CallTipShow(0, "alpha(value)");
                Check(editor->CallTipActive(), "calltip active");
                phase = 2;
            }
            else if (phase < 7)
            {
                editor->CallTipCancel();
                editor->AutoCompCancel();
                editor->AutoCompShow(0, "alpha beta");
                ++phase;
            }
            else
            {
                // Let GTK process deferred popup destruction before quitting.
                editor->AutoCompCancel();
                editor->Destroy();
                CallAfter([this] { Finish(0, "STC Unicode, lexer, completion and popup contracts passed"); });
                timer.Stop();
            }
        }
        catch (const std::exception& error) { Finish(1, error.what()); }
    }

public:
    bool OnInit() override
    {
        frame = new wxFrame(nullptr, wxID_ANY, "EmberBSD STC contract", wxDefaultPosition, wxSize(500, 350));
        editor = new wxStyledTextCtrl(frame);
        editor->Bind(wxEVT_STC_AUTOCOMP_SELECTION, [this](wxStyledTextEvent& event) {
            ++selections;
            selectionDataValid = selectionDataValid && event.GetText() == "alpha" &&
                                 event.GetPosition() == 0;
        });
        editor->Bind(wxEVT_STC_AUTOCOMP_SELECTION_CHANGE, [this](wxStyledTextEvent& event) {
            ++selectionChanges;
            selectionChangeValid = event.GetText() == "alpha" &&
                                   event.GetPosition() == 0 && event.GetListType() == 0;
        });
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Step(); });
        frame->Show();
        timer.Start(100);
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(STCContract);
