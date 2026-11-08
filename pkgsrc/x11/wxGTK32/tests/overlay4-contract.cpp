// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Run with a real GTK4 display and G_DEBUG=fatal-warnings.
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/dcclient.h>
#include <wx/dcmemory.h>
#include <wx/overlay.h>
#include <wx/private/overlay.h>
#include <wx/timer.h>
#include <cstdio>
#include <stdexcept>

#if !defined(__WXGTK4__) || !defined(wxHAS_GENERIC_OVERLAY) || defined(wxHAS_NATIVE_OVERLAY)
#error This contract requires the common GTK4 overlay.
#endif

static void Check(bool value, const char* message)
{
    if (!value) throw std::runtime_error(message);
}

static void CheckPixel(wxDC& dc, int x, int y, const wxColour& expected)
{
    wxColour actual;
    Check(dc.GetPixel(x, y, &actual) && actual == expected,
          "overlay did not preserve the expected pixels");
}

static void CheckOverlay(wxDC& dc)
{
    dc.SetBackground(*wxBLUE_BRUSH);
    dc.Clear();
    wxOverlay overlay;
    Check(!overlay.IsNative(), "GTK4 must use the common overlay implementation");
    {
        wxDCOverlay draw(overlay, &dc, 8, 8, 40, 40);
        dc.SetPen(*wxTRANSPARENT_PEN);
        dc.SetBrush(*wxRED_BRUSH);
        dc.DrawRectangle(0, 0, 64, 64);
        CheckPixel(dc, 24, 24, *wxRED);
        CheckPixel(dc, 2, 2, *wxBLUE);
        draw.Clear();
        CheckPixel(dc, 24, 24, *wxBLUE);
    }
    dc.DestroyClippingRegion();
    overlay.Reset();
    // Reset must capture the new background, not restore the preceding one.
    dc.SetBackground(*wxGREEN_BRUSH);
    dc.Clear();
    {
        wxDCOverlay draw(overlay, &dc, 8, 8, 40, 40);
        dc.SetBrush(*wxRED_BRUSH);
        dc.DrawRectangle(8, 8, 40, 40);
        draw.Clear();
        CheckPixel(dc, 24, 24, *wxGREEN);
    }
    dc.DestroyClippingRegion();
}

class OverlayContract : public wxApp
{
    wxFrame* frame = NULL;
    wxTimer timer;
    int result = 1;
    int ticks = 0;
    bool painted = false;
public:
    bool OnInit() wxOVERRIDE
    {
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 overlay contract",
                            wxDefaultPosition, wxSize(240, 180));
        frame->Bind(wxEVT_PAINT, [this](wxPaintEvent&) {
            wxPaintDC dc(frame);
            dc.SetBackground(*wxWHITE_BRUSH);
            dc.Clear();
            painted = true;
        });
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { RunChecks(); });
        frame->Show();
        timer.Start(100);
        return true;
    }
    int OnRun() wxOVERRIDE
    {
        wxApp::OnRun();
        return result;
    }
    void RunChecks()
    {
        if (!painted && ++ticks < 50) return;
        timer.Stop();
        try
        {
            Check(painted, "no real GTK4 paint occurred");
            for (int scale = 1; scale <= 2; ++scale)
            {
                wxBitmap bitmap(64 * scale, 64 * scale, 32);
                bitmap.SetScaleFactor(scale);
                wxMemoryDC dc(bitmap);
                CheckOverlay(dc);
            }
            {
                wxClientDC dc(frame);
                CheckOverlay(dc);
            }
            // A fresh DC must see the restored client content after commit.
            {
                wxClientDC dc(frame);
                CheckPixel(dc, 24, 24, *wxGREEN);
            }
            result = 0;
            std::puts("GTK4 overlay capture, clipping, clear and reset passed");
        }
        catch (const std::exception& error)
        {
            std::fprintf(stderr, "%s\n", error.what());
        }
        frame->Destroy();
        ExitMainLoop();
    }
};
wxIMPLEMENT_APP_NO_MAIN(OverlayContract);
int main(int argc, char** argv) { return wxEntry(argc, argv); }
