// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Run with a real GTK4 display and WebKit web process; no network is needed.
#include <wx/wx.h>
#include <wx/webview.h>
#include <wx/timer.h>
#include <webkit/webkit.h>
#include <cstdio>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract must link the GTK4 wxWidgets provider.
#endif

static void Check(bool ok, const char* what)
{
    if (!ok)
        throw std::runtime_error(what);
}

class ContractApp : public wxApp
{
    wxFrame* frame = NULL;
    wxWebView* view = NULL;
    wxTimer deadline;
    wxTimer advance;
    bool inScript = false;
    bool finished = false;
    int phase = 0;
    bool started = false;
    int messages = 0;
    int scriptResults = 0;
    int failures = 0;
    int navigationVetoes = 0;
    int exitCode = 1;
    int requestTag = 0;

    void Finish(int code, const char* reason)
    {
        if (finished)
            return;
        finished = true;
        deadline.Stop();
        advance.Stop();
        exitCode = code;
        std::fprintf(code ? stderr : stdout, "%s\n", reason);
        if (frame)
        {
            frame->Destroy();
            frame = NULL;
        }
        ExitMainLoop();
    }

    void MaybeFinish()
    {
        if (messages == 2 && scriptResults == 1 && failures == 1 && navigationVetoes == 1)
            Finish(0, "WebKit6 JS, messages, DOM, navigation, context-menu and errors PASS");
    }

    void RunChecks()
    {
        inScript = true;
        try
        {
            wxString value;
            Check(view->RunScript("({answer:42, text:'\\u03bb'})", &value), "object result");
            Check(value == wxString::FromUTF8("{\"answer\":42,\"text\":\"λ\"}"), "object JSON/UTF-8");
            Check(view->RunScript("undefined", &value) && value == "undefined", "undefined result");
            Check(view->RunScript("null", &value) && value == "null", "null result");
            Check(view->GetPageText().Contains("Alpha"), "page text");
            Check(view->GetPageSource().Contains("wx-contract"), "page source");
            Check(!view->HasSelection(), "empty selection");
            Check(view->GetSelectedText().empty() && view->GetSelectedSource().empty(), "empty selection data");
            Check(view->RunScript(
                "var r=document.createRange(); r.selectNodeContents(document.getElementById('pick'));"
                "var s=window.getSelection(); s.removeAllRanges(); s.addRange(r);"), "create selection");
            Check(view->RunScript("var originalSelection=window.getSelection;"
                                  "window.getSelection=function(){throw Error('author override');};"), "author override");
            Check(view->HasSelection(), "range selection in isolated world");
            Check(view->GetSelectedText() == "Alpha beta", "selected text");
            Check(view->GetSelectedSource() == "Alpha <b>beta</b>", "selected markup");
            view->ClearSelection();
            Check(!view->HasSelection(), "clear selection");
            Check(view->RunScript("window.getSelection=originalSelection;"), "restore page helper");
            Check(view->RunScript("var r=document.createRange();r.selectNodeContents(document.getElementById('pick'));"
                                  "r.collapse(true);window.getSelection().addRange(r);"), "collapsed range");
            Check(!view->HasSelection(), "collapsed range is not a selection");
            Check(view->RunScript("var s=window.getSelection();s.removeAllRanges();"
                                  "var r=document.createRange();r.selectNodeContents(document.getElementById('pick'));"
                                  "s.addRange(r);"), "select for deletion");
            view->DeleteSelection();
            Check(view->RunScript("document.getElementById('pick').innerHTML", &value) && value.empty(), "delete selection");

            view->EnableContextMenu(false);
            WebKitWebView* backend = static_cast<WebKitWebView*>(view->GetNativeBackend());
            WebKitContextMenu* menu = webkit_context_menu_new();
            WebKitHitTestResult* hit = WEBKIT_HIT_TEST_RESULT(g_object_new(WEBKIT_TYPE_HIT_TEST_RESULT, NULL));
            gboolean handled = FALSE;
            // API6 has no GdkEvent argument; a GTK3 callback misreads user_data.
            g_signal_emit_by_name(backend, "context-menu", menu, hit, &handled);
            g_object_unref(hit);
            g_object_unref(menu);
            Check(handled, "context-menu suppression");

            Check(view->AddScriptMessageHandler("wxBridge"), "register message channel");
            Check(!view->AddScriptMessageHandler("wxBridge"), "duplicate channel refusal");
            Check(view->RunScript("wxBridge.postMessage({phase:1});"), "post first message");
        }
        catch (const std::exception& e) { Finish(1, e.what()); }
        inScript = false;
    }

    void Advance()
    {
        if (!started || inScript || finished)
            return;
        try
        {
            if (phase == 0 && messages == 1)
            {
                phase = 1;
                inScript = true;
                Check(view->RemoveScriptMessageHandler("wxBridge"), "unregister channel");
                Check(view->AddScriptMessageHandler("wxBridge"), "re-register channel");
                Check(view->RunScript("wxBridge.postMessage({phase:2});"), "post second message");
                inScript = false;
            }
            else if (phase == 1 && messages == 2)
            {
                phase = 2;
                view->RunScriptAsync("throw new Error('wx-contract-error')", &requestTag);
            }
            else if (phase == 2 && scriptResults == 1)
            {
                phase = 3;
                view->LoadURL("https://wx-contract.invalid/veto");
            }
        }
        catch (const std::exception& e) { Finish(1, e.what()); }
    }

public:
    bool OnInit() override
    {
        frame = new wxFrame(NULL, wxID_ANY, "WebKit6 contract", wxDefaultPosition, wxSize(640, 480));
        view = wxWebView::New();
        Check(view != NULL, "WebView factory");
        view->Bind(wxEVT_WEBVIEW_LOADED, [this](wxWebViewEvent&) {
            if (!started && view->GetPageSource().Contains("wx-contract"))
            {
                started = true;
                CallAfter(&ContractApp::RunChecks);
            }
        });
        view->Bind(wxEVT_WEBVIEW_SCRIPT_RESULT, [this](wxWebViewEvent& e) {
            try
            {
                Check(e.GetClientData() == &requestTag, "async client data");
                Check(e.GetInt() == 0 && e.GetString().Contains("wx-contract-error"), "async JS error contract");
                Check(++scriptResults == 1, "one async completion");
                MaybeFinish();
            }
            catch (const std::exception& ex) { Finish(1, ex.what()); }
        });
        view->Bind(wxEVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, [this](wxWebViewEvent& e) {
            try
            {
                Check(++messages <= 2, "duplicate message delivery");
                Check(e.GetString() == wxString::Format("{\"phase\":%d}", messages), "message JSON");
                MaybeFinish();
            }
            catch (const std::exception& ex) { Finish(1, ex.what()); }
        });
        view->Bind(wxEVT_WEBVIEW_NAVIGATING, [this](wxWebViewEvent& e) {
            if (e.GetURL().Contains("/veto"))
            {
                e.Veto();
                ++navigationVetoes;
                CallAfter([this] {
                    GError* error = g_error_new_literal(G_IO_ERROR, G_IO_ERROR_CONNECTION_REFUSED, "contract refused");
                    gboolean handled = FALSE;
                    g_signal_emit_by_name(view->GetNativeBackend(), "load-failed", WEBKIT_LOAD_STARTED,
                                          "https://wx-contract.invalid/veto", error, &handled);
                    g_error_free(error);
                    MaybeFinish();
                });
            }
        });
        view->Bind(wxEVT_WEBVIEW_ERROR, [this](wxWebViewEvent& e) {
            try
            {
                Check(e.GetInt() == wxWEBVIEW_NAV_ERR_CONNECTION, "Gio network error category");
                Check(e.GetString() == "contract refused", "error description");
                Check(++failures == 1, "one navigation error");
            }
            catch (const std::exception& ex) { Finish(1, ex.what()); }
        });
        if (!view->Create(frame, wxID_ANY))
            return false;
        auto sizer = new wxBoxSizer(wxVERTICAL);
        sizer->Add(view, 1, wxEXPAND);
        frame->SetSizer(sizer);
        frame->Show();
        deadline.SetOwner(this);
        advance.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent& e) {
            if (e.GetId() == deadline.GetId())
                Finish(1, "WebKit6 contract timed out");
            else
                Advance();
        });
        deadline.StartOnce(30000);
        advance.Start(25);
        view->SetPage("<!doctype html><title>wx-contract</title><p id='pick'>Alpha <b>beta</b></p>",
                      "https://wx-contract.invalid/");
        return true;
    }

    int OnRun() override { wxApp::OnRun(); return exitCode; }
};
wxIMPLEMENT_APP(ContractApp);
