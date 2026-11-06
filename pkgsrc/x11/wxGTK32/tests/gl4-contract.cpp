// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Requires a real GTK4/EGL display. CPU reads here verify GPU output only;
// the wxGLCanvas presentation implementation does not read pixels to the CPU.
#include <epoxy/gl.h>
#include <EGL/egl.h>
#include <wx/wx.h>
#include <wx/glcanvas.h>
#include <gtk/gtk.h>
#include <cstdio>
#include <cstring>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}

class GLContract : public wxApp
{
    wxFrame* frame = NULL;
    wxGLCanvas* left = NULL;
    wxGLCanvas* right = NULL;
    wxGLContext* first = NULL;
    wxGLContext* second = NULL;
    GskRenderNode* retained = NULL;
    GLuint sharedTexture = 0;
    EGLContext firstNative = EGL_NO_CONTEXT, secondNative = EGL_NO_CONTEXT;
    EGLSurface rightSurface = EGL_NO_SURFACE;
    wxTimer timer;
    int phase = 0, ticks = 0, result = 1;
    bool finished = false;

    void Finish(int status, const char* text)
    {
        if (finished) return;
        finished = true;
        timer.Stop();
        result = status;
        if (sharedTexture && second && right && second->SetCurrent(*right))
            glDeleteTextures(1, &sharedTexture);
        if (retained) gsk_render_node_unref(retained);
        delete second;
        delete first;
        second = first = NULL;
        std::fprintf(status ? stderr : stdout, "%s\n", text);
        frame->Destroy();
        ExitMainLoop();
    }
    GskRenderNode* Capture(wxGLCanvas* canvas)
    {
        GtkWidget* widget = GTK_WIDGET(canvas->GetHandle());
        GdkPaintable* paintable = gtk_widget_paintable_new(widget);
        GtkSnapshot* snapshot = gtk_snapshot_new();
        gdk_paintable_snapshot(paintable, GDK_SNAPSHOT(snapshot),
                              gtk_widget_get_width(widget), gtk_widget_get_height(widget));
        g_object_unref(paintable);
        GskRenderNode* node = gtk_snapshot_free_to_node(snapshot);
        Check(node != NULL, "canvas produces a GTK snapshot");
        return node;
    }
    void CheckPattern(GskRenderNode* node, bool gray = false)
    {
        GtkNative* native = gtk_widget_get_native(GTK_WIDGET(frame->GetHandle()));
        GskRenderer* renderer = gtk_native_get_renderer(native);
        Check(renderer != NULL, "native GTK renderer exists");
        wxString allowSoftware;
        if (!wxGetEnv("WX_GL_ALLOW_SOFTWARE", &allowSoftware) || allowSoftware != "1")
            Check(std::strstr(G_OBJECT_TYPE_NAME(renderer), "Cairo") == NULL, "hardware GTK renderer required");
        GdkTexture* image = gsk_renderer_render_texture(renderer, node, NULL);
        Check(image != NULL, "retained GL texture renders");
        GdkTextureDownloader* downloader = gdk_texture_downloader_new(image);
        gdk_texture_downloader_set_format(downloader, GDK_MEMORY_R8G8B8A8);
        gsize stride = 0;
        GBytes* bytes = gdk_texture_downloader_download_bytes(downloader, &stride);
        const guint8* data = static_cast<const guint8*>(g_bytes_get_data(bytes, NULL));
        const int width = gdk_texture_get_width(image), height = gdk_texture_get_height(image);
        const guint8* top = data + (height / 4) * stride + (width / 2) * 4;
        const guint8* bottom = data + (3 * height / 4) * stride + (width / 2) * 4;
        const bool correct = gray ?
            top[0] >= 185 && top[0] <= 190 && top[1] >= 185 && top[1] <= 190 &&
            top[2] >= 185 && top[2] <= 190 && bottom[0] >= 185 && bottom[0] <= 190 :
                             top[2] > 240 && top[0] < 15 && top[1] < 15 &&
                             bottom[0] > 240 && bottom[1] < 15 && bottom[2] < 15;
        g_bytes_unref(bytes);
        gdk_texture_downloader_free(downloader);
        g_object_unref(image);
        Check(correct, gray ? "sRGB encoded values survive GPU copy and GTK colour conversion" :
              "immutable presented frame and GL-to-GTK vertical orientation");
    }
    void Start()
    {
        try
        {
            first = new wxGLContext(left);
            Check(first->IsOK() && first->SetCurrent(*left), "create desktop compatibility context");
            firstNative = eglGetCurrentContext();
            const EGLSurface leftSurface = eglGetCurrentSurface(EGL_DRAW);
            Check(firstNative != EGL_NO_CONTEXT && leftSurface != EGL_NO_SURFACE, "native EGL context and pbuffer");
            Check(gdk_gl_context_get_current() == NULL, "raw EGL binding clears GDK context cache");
            GLboolean nativeDoubleBuffer = GL_TRUE;
            glGetBooleanv(GL_DOUBLEBUFFER, &nativeDoubleBuffer);
            Check(nativeDoubleBuffer == GL_FALSE, "pbuffer framebuffer is explicitly single-buffered");
            GLint profile = 0;
            glGetIntegerv(GL_CONTEXT_PROFILE_MASK, &profile);
            Check(profile & GL_CONTEXT_COMPATIBILITY_PROFILE_BIT, "compatibility GL for KiCad immediate-mode calls");
            const char* renderer = reinterpret_cast<const char*>(glGetString(GL_RENDERER));
            std::printf("GL_RENDERER=%s\n", renderer ? renderer : "unknown");
            wxString allowSoftware;
            if (!wxGetEnv("WX_GL_ALLOW_SOFTWARE", &allowSoftware) || allowSoftware != "1")
                Check(renderer && !std::strstr(renderer, "llvmpipe") && !std::strstr(renderer, "softpipe"), "hardware GL renderer required");

            glGenTextures(1, &sharedTexture);
            glBindTexture(GL_TEXTURE_2D, sharedTexture);
            const guint8 white[] = {255, 255, 255, 255};
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, white);
            Check(first->SetCurrent(*right), "same wxGLContext can target another canvas");
            rightSurface = eglGetCurrentSurface(EGL_DRAW);
            Check(eglGetCurrentContext() == firstNative && rightSurface != leftSurface, "context identity preserved while drawable changes");
            second = new wxGLContext(right, first);
            Check(second->IsOK() && second->SetCurrent(*right), "create explicit shared context");
            secondNative = eglGetCurrentContext();
            Check(secondNative != firstNative && glIsTexture(sharedTexture), "distinct native contexts share GL resources");
            {
                wxGLContext independent(right);
                Check(independent.IsOK() && independent.SetCurrent(*right) && glIsTexture(sharedTexture),
                      "GTK4 contexts without explicit other still use display-wide resource sharing");
                Check(second->SetCurrent(*right), "restore explicit shared context");
            }
            {
                wxLogNull noDialogs;
                wxGLContextAttrs invalid;
                invalid.MajorVersion(99).EndList();
                wxGLContext rejected(right, NULL, &invalid);
                Check(!rejected.IsOK() && eglGetCurrentContext() == secondNative, "failed context creation preserves current context");
                wxGLAttributes stereo;
                stereo.RGBA().Stereo().EndList();
                Check(!wxGLCanvas::IsDisplaySupported(stereo), "unsupported visual attribute is rejected");
            }
            Check(first->SetCurrent(*left), "restore original context and canvas");
            glBindFramebuffer(GL_FRAMEBUFFER, 0);
            Check(glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE, "native default framebuffer zero is renderable");
            const int width = wxRound(left->GetClientSize().x * left->GetContentScaleFactor());
            const int height = wxRound(left->GetClientSize().y * left->GetContentScaleFactor());
            glViewport(0, 0, width, height);
            glDisable(GL_SCISSOR_TEST);
            glClearColor(1, 0, 0, 1);
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
            glEnable(GL_SCISSOR_TEST);
            glScissor(0, height / 2, width, height - height / 2);
            glClearColor(0, 0, 1, 1);
            glClear(GL_COLOR_BUFFER_BIT);
            glDisable(GL_SCISSOR_TEST);
            // KiCad's screenshot uses GL_BACK_LEFT even on this single-buffer
            // pbuffer. Mesa explicitly aliases its BACK names to FRONT storage.
            glDrawBuffer(GL_BACK);
            glReadBuffer(GL_BACK_LEFT);
            guint8 pixel[4] = {};
            glReadPixels(width / 2, height / 4, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
            Check(glGetError() == GL_NO_ERROR && pixel[0] > 240 && pixel[1] < 15 && pixel[2] < 15,
                  "KiCad FB0 GL_BACK drawing and GL_BACK_LEFT readback remain valid");
            Check(left->SwapBuffers(), "publish GPU frame");
            Check(eglGetCurrentContext() == firstNative, "swap preserves native current context");
            // Mutating the native back buffer must not mutate GTK's front frame.
            glClearColor(0, 1, 0, 1);
            glClear(GL_COLOR_BUFFER_BIT);
            phase = 1;
            ticks = 0;
            timer.Start(50);
        }
        catch (const std::exception& e) { Finish(1, e.what()); }
    }
    void Poll()
    {
        try
        {
            Check(++ticks < 200, "GTK4 GL runtime timeout");
            if (ticks < 4) return; // allow GTK to snapshot and present a frame
            if (phase == 1)
            {
                retained = Capture(left);
                CheckPattern(retained);
                delete first;
                first = NULL;
                left->Destroy();
                left = NULL;
                frame->SetSize(900, 500);
                frame->Layout();
                phase = 2;
                ticks = 0;
            }
            else if (phase == 2)
            {
                CheckPattern(retained); // frame outlives its source canvas/context
                Check(second->SetCurrent(*right) && glIsTexture(sharedTexture), "share group survives original context destruction");
                Check(eglGetCurrentContext() == secondNative && eglGetCurrentSurface(EGL_DRAW) != rightSurface,
                      "resize replaces pbuffer while retaining requested context");
                glBindFramebuffer(GL_FRAMEBUFFER, 0);
                GLint encoding = 0;
                glGetFramebufferAttachmentParameteriv(GL_FRAMEBUFFER, GL_FRONT_LEFT,
                    GL_FRAMEBUFFER_ATTACHMENT_COLOR_ENCODING, &encoding);
                Check(encoding == GL_SRGB, "requested EGL sRGB framebuffer exists");
                glEnable(GL_FRAMEBUFFER_SRGB);
                glClearColor(0.5f, 0.5f, 0.5f, 1);
                glClear(GL_COLOR_BUFFER_BIT);
                // A snapshot must ignore application pixel-transfer/scissor
                // state, yet preserve it for the next application operation.
                glPixelTransferf(GL_RED_SCALE, 0.25f);
                glEnable(GL_SCISSOR_TEST);
                glScissor(0, 0, 0, 0);
                Check(right->SwapBuffers() && eglGetCurrentContext() == secondNative, "surviving canvas renders and presents");
                GLfloat redScale = 0;
                glGetFloatv(GL_RED_SCALE, &redScale);
                Check(redScale == 0.25f && glIsEnabled(GL_SCISSOR_TEST) && glIsEnabled(GL_FRAMEBUFFER_SRGB),
                      "swap preserves caller pixel-transfer, scissor and sRGB state");
                glPixelTransferf(GL_RED_SCALE, 1);
                glDisable(GL_SCISSOR_TEST);
                phase = 3;
                ticks = 0;
            }
            else if (phase == 3)
            {
                GskRenderNode* srgb = Capture(right);
                CheckPattern(srgb, true);
                gsk_render_node_unref(srgb);
                Finish(0, "GTK4 GL identity, display sharing, FB0/BACK, GPU presentation, sRGB, resize and retained lifetime PASS");
            }
        }
        catch (const std::exception& e) { Finish(1, e.what()); }
    }
public:
    bool OnInit() override
    {
        wxLog::SetActiveTarget(new wxLogStderr);
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 GL contract", wxDefaultPosition, wxSize(640, 360));
        wxGLAttributes attrs;
        attrs.RGBA().DoubleBuffer().Depth(8).EndList();
        left = new wxGLCanvas(frame, attrs);
        wxGLAttributes srgb;
        srgb.RGBA().DoubleBuffer().Depth(8).FrameBuffersRGB().EndList();
        right = new wxGLCanvas(frame, srgb);
        if (!left->GetHandle() || !right->GetHandle())
        {
            Finish(1, "required EGL ordinary and sRGB visuals unavailable");
            return false;
        }
        auto sizer = new wxBoxSizer(wxHORIZONTAL);
        sizer->Add(left, 1, wxEXPAND);
        sizer->Add(right, 1, wxEXPAND);
        frame->SetSizer(sizer);
        for (wxGLCanvas* canvas : {left, right})
            canvas->Bind(wxEVT_PAINT, [canvas](wxPaintEvent&) { wxPaintDC dc(canvas); });
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Poll(); });
        frame->Show();
        CallAfter(&GLContract::Start);
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(GLContract);
