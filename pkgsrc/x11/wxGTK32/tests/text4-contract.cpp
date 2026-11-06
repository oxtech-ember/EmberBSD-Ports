// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Requires a real GTK4 display and an installed English en_US dictionary.
#include <wx/wx.h>
#include <wx/textctrl.h>
#include <wx/timer.h>
#include <gtk/gtk.h>
#include <cstdio>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires the GTK4 provider.
#endif
#if !wxUSE_SPELLCHECK
#error Spellchecking must remain enabled.
#endif

static void Check(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}
static bool EntryHasError(GtkEntry* entry)
{
    PangoAttrList* attrs = gtk_entry_get_attributes(entry);
    if (!attrs) return false;
    PangoAttrIterator* iter = pango_attr_list_get_iterator(attrs);
    bool found = false;
    do
    {
        PangoAttribute* attr = pango_attr_iterator_get(iter, PANGO_ATTR_UNDERLINE);
        if (attr && reinterpret_cast<PangoAttrInt*>(attr)->value == PANGO_UNDERLINE_ERROR)
            found = true;
    } while (pango_attr_iterator_next(iter));
    pango_attr_iterator_destroy(iter);
    return found;
}
static bool BufferHasError(GtkTextBuffer* buffer)
{
    GtkTextIter iter;
    gtk_text_buffer_get_iter_at_offset(buffer, &iter, 1);
    GSList* tags = gtk_text_iter_get_tags(&iter);
    bool found = false;
    for (GSList* p = tags; p; p = p->next)
    {
        int underline = PANGO_UNDERLINE_NONE;
        g_object_get(p->data, "underline", &underline, NULL);
        if (underline == PANGO_UNDERLINE_ERROR) found = true;
    }
    g_slist_free(tags);
    return found;
}

class TextContract : public wxApp
{
    wxFrame* frame = NULL;
    wxTextCtrl* entry = NULL;
    wxTextCtrl* multi = NULL;
    GtkWidget* nativeEntry = NULL;
    GtkWidget* nativeView = NULL;
    GtkTextBuffer* buffer = NULL;
    wxTimer timer;
    int entryEvents = 0, multiEvents = 0, ticks = 0, phase = 0, result = 1;
    bool finished = false;

    void Finish(int status, const char* message)
    {
        if (finished) return;
        finished = true;
        timer.Stop();
        result = status;
        std::fprintf(status ? stderr : stdout, "%s\n", message);
        frame->Destroy();
        ExitMainLoop();
    }
    void Start()
    {
        try
        {
            entryEvents = multiEvents = 0;
            entry->SetValue("alpha");
            Check(entryEvents == 1, "SetValue emits one text event");
            entry->ChangeValue("beta");
            Check(entryEvents == 1, "ChangeValue suppresses events");
            gtk_editable_select_region(GTK_EDITABLE(nativeEntry), 0, -1);
            GtkEditable* delegate = gtk_editable_get_delegate(GTK_EDITABLE(nativeEntry));
            entryEvents = 0;
            g_signal_emit_by_name(delegate, "insert-at-cursor", "lambda");
            Check(entry->GetValue() == "lambda", "native selection replacement");
            Check(entryEvents == 1, "native GtkText edit emits one event");
            g_signal_emit_by_name(delegate, "insert-at-cursor", "x");
            Check(entryEvents == 2, "separate native edits are not merged");
            entry->SetMaxLength(6);
            entry->ChangeValue("abc");
            entry->SetInsertionPointEnd();
            entry->WriteText("def");
            Check(entry->GetValue() == "abcdef", "entry maximum length boundary");
            entry->SetMaxLength(0);

            multi->ChangeValue(wxString::FromUTF8("αβγ"));
            multi->SetSelection(1, 2);
            Check(multi->GetStringSelection() == wxString::FromUTF8("β"), "Unicode selection offsets");
            multiEvents = 0;
            GtkTextIter a, b;
            gtk_text_buffer_get_iter_at_offset(buffer, &a, 1);
            gtk_text_buffer_get_iter_at_offset(buffer, &b, 2);
            gtk_text_buffer_begin_user_action(buffer);
            gtk_text_buffer_delete(buffer, &a, &b);
            gtk_text_buffer_insert(buffer, &a, "x", -1);
            gtk_text_buffer_end_user_action(buffer);
            Check(multi->GetValue() == wxString::FromUTF8("αxγ"), "native multiline replacement");
            Check(multiEvents == 1, "buffer user action emits one text event");
            wxTextAttr style;
            style.SetTextColour(*wxRED);
            style.SetFontUnderlined(wxTEXT_ATTR_UNDERLINE_DOUBLE);
            Check(multi->SetStyle(0, 2, style), "set native text style");
            wxTextAttr read;
            Check(multi->GetStyle(1, read), "read native text style");
            Check(read.GetTextColour() == *wxRED &&
                  read.GetUnderlineType() == wxTEXT_ATTR_UNDERLINE_DOUBLE, "style round trip");

            entry->ChangeValue("helo ");
            multi->ChangeValue("helo ");
            // libspelling does not underline the word currently being typed.
            entry->SetInsertionPointEnd();
            multi->SetInsertionPointEnd();
            const auto options = wxTextProofOptions::Default().Language("en_US");
            Check(entry->EnableProofCheck(options), "enable entry spelling");
            Check(multi->EnableProofCheck(options), "enable multiline spelling");
            Check(entry->GetProofCheckOptions().IsSpellCheckEnabled(), "entry spelling state");
            Check(multi->GetProofCheckOptions().IsSpellCheckEnabled(), "multiline spelling state");
            phase = 1;
            timer.Start(25);
        }
        catch (const std::exception& e) { Finish(1, e.what()); }
    }
    void Poll()
    {
        try
        {
            Check(++ticks < 1000, "spelling timeout: GTK4 display, libspelling and en_US dictionary are required");
            if (phase == 1 && EntryHasError(GTK_ENTRY(nativeEntry)) && BufferHasError(buffer))
            {
                entryEvents = multiEvents = 0;
                entry->SetInsertionPoint(1);
                multi->SetInsertionPoint(1);
                Check(gtk_widget_activate_action(nativeEntry, "spelling.correct", "s", "hello"), "entry correction action");
                Check(gtk_widget_activate_action(nativeView, "spelling.correct", "s", "hello"), "multiline correction action");
                Check(entry->GetValue() == "hello " && multi->GetValue() == "hello ", "both corrections applied");
                Check(entryEvents == 1 && multiEvents == 1, "correction event counts");
                Check(entry->EnableProofCheck(wxTextProofOptions::Disable()), "disable entry spelling");
                Check(multi->EnableProofCheck(wxTextProofOptions::Disable()), "disable multiline spelling");
                Check(!entry->GetProofCheckOptions().IsSpellCheckEnabled(), "disabled entry state");
                Check(!multi->GetProofCheckOptions().IsSpellCheckEnabled(), "disabled multiline state");
                phase = 2;
            }
            if (phase == 2 && !EntryHasError(GTK_ENTRY(nativeEntry)) && !BufferHasError(buffer))
                Finish(0, "GTK4 text editing, events, Unicode, styles and libspelling corrections PASS");
        }
        catch (const std::exception& e) { Finish(1, e.what()); }
    }
public:
    bool OnInit() override
    {
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 text contract", wxDefaultPosition, wxSize(640, 480));
        entry = new wxTextCtrl(frame, wxID_ANY);
        multi = new wxTextCtrl(frame, wxID_ANY, "", wxDefaultPosition, wxDefaultSize, wxTE_MULTILINE);
        auto sizer = new wxBoxSizer(wxVERTICAL);
        sizer->Add(entry, 0, wxEXPAND);
        sizer->Add(multi, 1, wxEXPAND);
        frame->SetSizer(sizer);
        nativeEntry = GTK_WIDGET(entry->GetHandle());
        nativeView = gtk_scrolled_window_get_child(GTK_SCROLLED_WINDOW(multi->GetHandle()));
        buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(nativeView));
        entry->Bind(wxEVT_TEXT, [this](wxCommandEvent&) { ++entryEvents; });
        multi->Bind(wxEVT_TEXT, [this](wxCommandEvent&) { ++multiEvents; });
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Poll(); });
        frame->Show();
        CallAfter(&TextContract::Start);
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(TextContract);
