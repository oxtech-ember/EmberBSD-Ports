// Origin: EmberBSD contributors (AI-assisted). SPDX-License-Identifier: GPL-3.0-or-later
// Link with the actual common/kicad_gl/gl_context_mgr.cpp and installed wxGTK4.
#include <kicad_gl/gl_context_mgr.h>
#include <trace_helpers.h>
#include <wx/wx.h>
#include <EGL/egl.h>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>

#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif

// The manager's only KiCad diagnostic dependency; the manager itself is unchanged.
const wxChar* const traceGalContext = wxT( "KICAD_GAL_CONTEXT" );

static void Check( bool condition, const char* message )
{
    if( !condition )
        throw std::runtime_error( message );
}

class GLContextContract : public wxApp
{
    wxFrame* frame = nullptr;
    wxGLCanvas* canvas = nullptr;
    wxGLCanvas* other = nullptr;
    GL_CONTEXT_MANAGER manager;
    int result = 1;

    void Run()
    {
        try
        {
            wxGLContext* context = manager.CreateCtx( canvas );
            Check( context != nullptr, "create managed context" );
            bool current = manager.LockCtx( context, nullptr );
            EGLContext native = eglGetCurrentContext();
            manager.UnlockCtx( context );
            Check( current && native != EGL_NO_CONTEXT, "shown canvas makes real context current" );

            for( int i = 0; i < 2; ++i )
            {
                canvas->Hide();
                current = manager.LockCtx( context, nullptr );
                manager.UnlockCtx( context );
                Check( !current, "hidden canvas is rejected without an assertion" );

                canvas->Show();
                current = manager.LockCtx( context, nullptr );
                manager.UnlockCtx( context );
                Check( current && eglGetCurrentContext() == native,
                       "shown canvas recovers the same context and releases the mutex" );
            }

            current = manager.LockCtx( context, other );
            manager.UnlockCtx( context );
            Check( current && eglGetCurrentContext() == native,
                   "explicit alternate canvas retains context identity" );

            // GTK4 pbuffers remain usable when the parent is hidden during teardown.
            frame->Hide();
            current = manager.LockCtx( context, nullptr );
            manager.UnlockCtx( context );
            Check( current, "hidden parent does not invalidate the canvas pbuffer" );
            manager.DestroyCtx( context );
            result = 0;
            std::puts( "KiCad GTK4 GL manager visibility, relock and override PASS" );
        }
        catch( const std::exception& error )
        {
            std::fprintf( stderr, "%s\n", error.what() );
        }

        manager.DeleteAll();
        frame->Destroy();
        ExitMainLoop();
    }

public:
    bool OnInit() override
    {
        wxSetAssertHandler( []( const wxString&, int, const wxString&, const wxString&,
                                const wxString& ) { std::fputs( "wx assertion\n", stderr ); std::exit( 2 ); } );
        frame = new wxFrame( nullptr, wxID_ANY, "KiCad GL manager contract", wxDefaultPosition,
                             wxSize( 240, 160 ) );
        const int attributes[] = { WX_GL_RGBA, WX_GL_DOUBLEBUFFER, WX_GL_DEPTH_SIZE, 24, 0 };
        canvas = new wxGLCanvas( frame, wxID_ANY, attributes );
        other = new wxGLCanvas( frame, wxID_ANY, attributes );
        frame->Show();
        CallAfter( &GLContextContract::Run );
        return true;
    }

    int OnRun() override
    {
        wxApp::OnRun();
        return result;
    }
};

wxIMPLEMENT_APP_NO_MAIN( GLContextContract );
int main( int argc, char** argv )
{
    return wxEntry( argc, argv );
}
