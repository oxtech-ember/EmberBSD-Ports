// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/clipbrd.h>
#include <wx/dataobj.h>
#include <wx/evtloop.h>
#include <wx/gtk/private/transfer4.h>
#include <wx/image.h>
#if wxUSE_LIBPNG
#include <wx/imagpng.h>
#endif
#include <gtk/gtk.h>
#include <cstdio>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <vector>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }
template<class Predicate> static void Until(Predicate done)
{
    const gint64 deadline = g_get_monotonic_time() + 5000000;
    while (!done())
    {
        Check(g_get_monotonic_time() < deadline, "asynchronous clipboard timeout");
        Check(wxEventLoopBase::GetActive()->DispatchTimeout(10) != 0, "event loop exited during clipboard check");
    }
}
struct TextResult { bool done = false, success = false; wxString text; };
static wxString NativeText(GdkClipboard* clipboard)
{
    typedef std::shared_ptr<TextResult> Result;
    Result result(new TextResult);
    gdk_clipboard_read_text_async(clipboard, NULL, [](GObject* source, GAsyncResult* async, void* data)
    {
        std::unique_ptr<Result> holder(static_cast<Result*>(data));
        GError* error = NULL;
        char* text = gdk_clipboard_read_text_finish(GDK_CLIPBOARD(source), async, &error);
        (*holder)->success = text != NULL && error == NULL;
        if (text) (*holder)->text = wxString::FromUTF8(text);
        g_free(text); g_clear_error(&error);
        (*holder)->done = true;
    }, new Result(result));
    Until([&] { return result->done; });
    Check(result->success, "native GTK text read succeeds");
    return result->text;
}

// A real provider callback destroys the requesting wxClipboard. It exercises
// request cancellation and late async callbacks without a mock transport.
// GObject calls destructive_provider_init, not a C++ constructor.
// cppcheck-suppress uninitMemberVarNoCtor
struct DestructiveProvider { GdkContentProvider parent; wxClipboard** victim; };
struct DestructiveProviderClass { GdkContentProviderClass parent; };
G_DEFINE_TYPE(DestructiveProvider, destructive_provider, GDK_TYPE_CONTENT_PROVIDER)
static GdkContentFormats* DestructiveFormats(GdkContentProvider*)
{
    const char* formats[] = { "application/x-wx-clipboard-lifetime-test" };
    return gdk_content_formats_new(formats, 1);
}
static void DestructiveWrite(GdkContentProvider* provider, const char*, GOutputStream*,
                            int priority, GCancellable* cancel, GAsyncReadyCallback callback, void* data)
{
    GTask* task = g_task_new(provider, cancel, callback, data);
    g_task_set_priority(task, priority);
    auto self = reinterpret_cast<DestructiveProvider*>(provider);
    if (self->victim && *self->victim)
    {
        wxClipboard* victim = *self->victim;
        *self->victim = NULL;
        delete victim;
    }
    g_task_return_new_error(task, G_IO_ERROR, G_IO_ERROR_CANCELLED, "test owner destruction");
    g_object_unref(task);
}
static void destructive_provider_class_init(DestructiveProviderClass* klass)
{
    auto provider = GDK_CONTENT_PROVIDER_CLASS(klass);
    provider->ref_formats = DestructiveFormats;
    provider->ref_storable_formats = DestructiveFormats;
    provider->write_mime_type_async = DestructiveWrite;
    provider->write_mime_type_finish = [](GdkContentProvider*, GAsyncResult* result, GError** error) -> gboolean
        { return g_task_propagate_boolean(G_TASK(result), error); };
}
static void destructive_provider_init(DestructiveProvider* self) { self->victim = NULL; }

// Real GCancellable signals are synchronous: owner teardown may reenter Cancel.
static void ReentrantCancellation()
{
    wxGTKTransfer::Requests requests;
    auto first = std::make_shared<wxGTKTransfer::Operation>();
    auto second = std::make_shared<wxGTKTransfer::Operation>();
    requests.Add(first); requests.Add(second);
    unsigned notifications = 0;
    g_signal_connect(first->cancel, "cancelled", G_CALLBACK(+[](GCancellable*, void* data)
        { static_cast<wxGTKTransfer::Requests*>(data)->Cancel(); }), &requests);
    g_signal_connect(second->cancel, "cancelled", G_CALLBACK(+[](GCancellable*, void* data)
        { ++*static_cast<unsigned*>(data); }), &notifications);
    requests.Cancel();
    Check(g_cancellable_is_cancelled(first->cancel) && g_cancellable_is_cancelled(second->cancel),
          "recursive cancellation cancels every detached request");
    Check(notifications == 1 && requests.pending.empty(), "each pending request is cancelled once");
}

class ClipboardContract : public wxApp
{
    wxFrame* frame = NULL;
    int result = 1;
    void Run()
    {
        try
        {
            ReentrantCancellation();
            GdkClipboard* native = gdk_display_get_clipboard(gdk_display_get_default());
            wxClipboard clipboard;
            Check(clipboard.Open(), "open clipboard");
            const wxString text = wxString::FromUTF8("clipboard — Ελληνικά — 日本語");
            Check(clipboard.SetData(new wxTextDataObject(text)), "offer Unicode text");
            Check(NativeText(native) == text, "wx data is readable through GTK native text API");
            wxTextDataObject received;
            Check(clipboard.GetData(received) && received.GetText() == text, "wx Unicode round trip");
            const unsigned char bytes[] = { 0, 1, 0xff, 0, 7 };
            const wxDataFormat binary("application/x-wx-transfer-test");
            auto custom = new wxCustomDataObject(binary);
            custom->SetData(sizeof(bytes), bytes);
            Check(clipboard.AddData(custom), "add custom binary data");
            Check(NativeText(native) == text, "AddData retains the earlier text offer");
            wxCustomDataObject binaryReceived(binary);
            Check(clipboard.GetData(binaryReceived) && binaryReceived.GetSize() == sizeof(bytes) &&
                  std::memcmp(binaryReceived.GetData(), bytes, sizeof(bytes)) == 0, "binary lengths and embedded zeroes preserved");
            bool notified = false;
            wxEvtHandler sink;
            sink.Bind(wxEVT_CLIPBOARD_CHANGED, [&](wxClipboardEvent& event)
            {
                Check(event.SupportsFormat(binary) && event.SupportsFormat(wxDF_UNICODETEXT), "async formats describe both offers");
                notified = true;
            });
            Check(clipboard.IsSupportedAsync(&sink), "request async format notification");
            Until([&] { return notified; });
            Check(clipboard.SetData(new wxTextDataObject("replacement")) && !clipboard.IsSupported(binary),
                  "SetData replaces earlier formats");
            gdk_clipboard_set_text(native, "native text");
            clipboard.Clear();
            Check(NativeText(native) == "native text", "Clear does not erase another owner's data");
            Check(clipboard.GetData(received) && received.GetText() == "native text", "GTK native G_TYPE_STRING deserializes into wx");
            GBytes* plainBytes = g_bytes_new_static("caf\303\251", 5);
            GdkContentProvider* plain = gdk_content_provider_new_for_bytes("text/plain", plainBytes);
            Check(gdk_clipboard_set_content(native, plain), "offer external plain UTF8 bytes");
            g_object_unref(plain); g_bytes_unref(plainBytes);
            Check(clipboard.GetData(received) && received.GetText() == wxString::FromUTF8("café"),
                  "plain UTF8 MIME interoperates with wx Unicode text");
            auto empty = new wxCustomDataObject(binary);
            Check(empty->SetData(0, bytes), "initialize empty custom payload");
            Check(clipboard.SetData(empty), "offer empty custom payload");
            Check(clipboard.GetData(binaryReceived) && binaryReceived.GetSize() == 0, "empty custom payload is valid");
            Check(clipboard.SetData(new wxTextDataObject("clipboard")), "restore clipboard text");
            clipboard.UsePrimarySelection(true);
            if (clipboard.SetData(new wxTextDataObject("primary")))
            {
                Check(clipboard.GetData(received) && received.GetText() == "primary", "primary selection round trip");
                Check(NativeText(native) == "clipboard", "primary does not overwrite clipboard");
                Check(!clipboard.Flush(), "primary selection is not persisted");
                clipboard.Clear();
            }
            else
                std::puts("Primary selection unavailable on this compositor; no primary protocol claimed");
            clipboard.UsePrimarySelection(false);
#if wxUSE_LIBPNG
            if (!wxImage::FindHandler(wxBITMAP_TYPE_PNG)) wxImage::AddHandler(new wxPNGHandler);
            wxImage image(2, 2);
            image.SetRGB(wxRect(0, 0, 2, 2), 17, 99, 201);
            wxBitmapDataObject encoded{wxBitmap(image)};
            std::vector<unsigned char> png(encoded.GetDataSize());
            Check(!png.empty() && encoded.GetDataHere(png.data()), "PNG data encoded");
            const unsigned char end[] = { 0, 0, 0, 0, 'I', 'E', 'N', 'D', 0xae, 0x42, 0x60, 0x82 };
            Check(png.size() >= sizeof(end) && std::memcmp(png.data() + png.size() - sizeof(end), end, sizeof(end)) == 0,
                  "PNG payload ends at IEND without exposing spare allocation bytes");
            Check(clipboard.SetData(new wxBitmapDataObject(wxBitmap(image))), "offer bitmap");
            wxBitmapDataObject restored;
            Check(clipboard.GetData(restored) && restored.GetBitmap().GetSize() == wxSize(2, 2), "PNG bitmap round trip");
#else
            std::puts("PNG handler is absent in this diagnostic configuration; PNG runtime contract not executed");
#endif
            clipboard.Close();
            wxClipboard* victim = new wxClipboard;
            Check(victim->Open(), "open temporary clipboard");
            auto provider = reinterpret_cast<DestructiveProvider*>(g_object_new(destructive_provider_get_type(), NULL));
            provider->victim = &victim;
            struct Cleanup
            {
                DestructiveProvider* provider;
                wxClipboard*& victim;
                GdkClipboard* native;
                Cleanup(DestructiveProvider* p, wxClipboard*& v, GdkClipboard* n)
                    : provider(p), victim(v), native(n) {}
                Cleanup(const Cleanup&) = delete;
                Cleanup& operator=(const Cleanup&) = delete;
                ~Cleanup()
                {
                    provider->victim = NULL;
                    if (gdk_clipboard_get_content(native) == GDK_CONTENT_PROVIDER(provider))
                        gdk_clipboard_set_content(native, NULL);
                    g_object_unref(provider);
                    delete victim;
                }
            } cleanup = { provider, victim, native };
            Check(gdk_clipboard_set_content(native, GDK_CONTENT_PROVIDER(provider)), "install real destructive provider");
            wxCustomDataObject cancelled(wxDataFormat("application/x-wx-clipboard-lifetime-test"));
            const bool success = victim->GetData(cancelled);
            Check(!success, "destroyed owner's transfer fails");
            Check(victim == NULL, "real provider destroyed the requesting clipboard");
            result = 0;
            std::puts("GTK4 clipboard MIME, ownership, async and cancellation contracts PASS");
        }
        catch (const std::exception& error)
        { std::fprintf(stderr, "FAIL: %s\n", error.what()); }
        frame->Destroy();
    }
public:
    bool OnInit() wxOVERRIDE
    {
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 clipboard contract");
        frame->Show();
        CallAfter([this] { Run(); });
        return true;
    }
    int OnExit() wxOVERRIDE { return result; }
};
wxIMPLEMENT_APP(ClipboardContract);
