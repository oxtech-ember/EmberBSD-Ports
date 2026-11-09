// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Compile with the selected source header before installed wx headers.
#include <wx/init.h>
#include <wx/dataobj.h>
// Avoid resolving inline helpers to an older installed wx DSO definition.
#define wxGTKTransfer wxGTKTransferContract
#include <wx/gtk/private/transfer4.h>
#undef wxGTKTransfer
#include <cstdio>
#include <cstring>

static bool Check(GdkClipboard* clipboard, const char* expectedMime)
{
    const wxDataFormat format(wxDF_UNICODETEXT);
    const char* mime = wxGTKTransferContract::Match(gdk_clipboard_get_formats(clipboard), format);
    if (!mime || strcmp(mime, expectedMime))
    {
        std::fprintf(stderr, "FAIL: MIME expected %s, selected %s\n", expectedMime, mime ? mime : "NULL");
        return false;
    }
    auto operation = wxGTKTransferContract::Read(G_OBJECT(clipboard), mime);
    const guint timeout = g_timeout_add_seconds(5, [](void* data) -> gboolean
    {
        g_cancellable_cancel(static_cast<wxGTKTransferContract::Operation*>(data)->cancel);
        return G_SOURCE_CONTINUE;
    }, operation.get());
    while (!operation->done)
        g_main_context_iteration(NULL, TRUE);
    g_source_remove(timeout);
    wxTextDataObject received;
    if (!operation->success || !operation->bytes ||
        !wxGTKTransferContract::Receive(received, format, operation->bytes) ||
        received.GetText() != wxString::FromUTF8("caf\303\251"))
    {
        std::fprintf(stderr, "FAIL: %s does not transfer Unicode text\n", expectedMime);
        return false;
    }
    return true;
}

int main()
{
    wxInitializer initialize;
    if (!initialize.IsOk() || !gtk_init_check()) return 2;
    GdkDisplay* display = gdk_display_get_default();
    if (!display) return 2;
    GdkClipboard* clipboard = gdk_display_get_clipboard(display);
    GBytes* bytes = g_bytes_new_static("caf\303\251", 5);
    GdkContentProvider* plain = gdk_content_provider_new_for_bytes("text/plain", bytes);
    bool ok = gdk_clipboard_set_content(clipboard, plain) && Check(clipboard, "text/plain");
    g_object_unref(plain);

    GdkContentProvider* providers[] = {
        gdk_content_provider_new_for_bytes("text/plain", bytes),
        gdk_content_provider_new_for_bytes("text/plain;charset=utf-8", bytes)
    };
    GdkContentProvider* both = gdk_content_provider_new_union(providers, 2);
    ok = (gdk_clipboard_set_content(clipboard, both) && Check(clipboard, "text/plain;charset=utf-8")) && ok;
    g_object_unref(both);
    g_bytes_unref(bytes);

    gdk_clipboard_set_text(clipboard, "caf\303\251");
    ok = Check(clipboard, "text/plain;charset=utf-8") && ok;
    // Local drops can expose a native GType without MIME types. Preserve
    // serializer selection for this path; the typed clipboard above tests IO.
    GdkContentFormats* typed = gdk_content_formats_new_for_gtype(G_TYPE_STRING);
    const char* mime = wxGTKTransferContract::Match(typed, wxDataFormat(wxDF_UNICODETEXT));
    if (!mime || strcmp(mime, "text/plain;charset=utf-8"))
    {
        std::fprintf(stderr, "FAIL: native G_TYPE_STRING serialization missing\n");
        ok = false;
    }
    gdk_content_formats_unref(typed);
    gdk_clipboard_set_content(clipboard, NULL);
    if (ok) std::puts("PASS: advertised plain/UTF8 MIME and native string transfer");
    return ok ? 0 : 1;
}
