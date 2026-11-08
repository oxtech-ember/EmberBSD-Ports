// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
#include <wx/app.h>
#include <wx/frame.h>
#include <wx/dcclient.h>
#include <wx/graphics.h>
#include <wx/region.h>
#include <wx/timer.h>
#include <wx/log.h>
#include <gtk/gtk.h>
#ifdef GDK_WINDOWING_X11
#include <gdk/x11/gdkx.h>
#include <X11/extensions/shape.h>
#endif
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#ifndef __WXGTK4__
#error This contract requires wxGTK4.
#endif
static void Check(bool ok, const char* message)
{ if (!ok) throw std::runtime_error(message); }
class ShapeContract : public wxApp
{
    wxFrame* frame = NULL;
    wxTimer timer;
    bool supported = false;
    int step = 0, result = 1;
    wxRegion Region() const
    {
        wxRegion region(0, 0, 140, 100);
        region.Subtract(40, 30, 20, 20);
        return region;
    }
    GdkSurface* Surface() const
    { return gtk_native_get_surface(gtk_widget_get_native(frame->m_widget)); }
#ifdef GDK_WINDOWING_X11
    bool Contains(int kind, int x, int y)
    {
        GdkSurface* surface = Surface();
        Check(surface && GDK_IS_X11_SURFACE(surface), "expected realized X11 surface");
        double dx, dy;
        gtk_native_get_surface_transform(gtk_widget_get_native(frame->m_widget), &dx, &dy);
        const double scale = gdk_surface_get_scale(surface);
        const int px = int(std::floor((x + dx) * scale));
        const int py = int(std::floor((y + dy) * scale));
        int count = 0, ordering;
        XRectangle* rects = XShapeGetRectangles(
            gdk_x11_display_get_xdisplay(gdk_surface_get_display(surface)),
            gdk_x11_surface_get_xid(surface), kind, &count, &ordering);
        bool found = false;
        for (int i = 0; i < count; ++i)
            if (px >= rects[i].x && px < rects[i].x + rects[i].width &&
                py >= rects[i].y && py < rects[i].y + rects[i].height)
                found = true;
        if (rects) XFree(rects);
        return found;
    }
    void CheckRegion()
    {
        for (int kind : {ShapeBounding, ShapeInput})
        {
            Check(Contains(kind, 10, 10), "shape excludes its visible interior");
            Check(!Contains(kind, 50, 40), "shape does not cut out the hole");
            Check(!Contains(kind, 200, 150), "shape retains the rectangular exterior");
        }
    }
    void CheckClear()
    {
        GdkSurface* surface = Surface();
        Bool bounding, clip;
        int bx, by, cx, cy;
        unsigned bw, bh, cw, ch;
        Check(XShapeQueryExtents(gdk_x11_display_get_xdisplay(gdk_surface_get_display(surface)),
                                gdk_x11_surface_get_xid(surface), &bounding, &bx, &by, &bw, &bh,
                                &clip, &cx, &cy, &cw, &ch) != 0 && !bounding,
              "Clear leaves a visual bounding shape installed");
        Check(Contains(ShapeInput, 50, 40) && Contains(ShapeInput, 200, 150),
              "Clear leaves the old input hole or exterior exclusion installed");
    }
#endif
    void Finish()
    {
        timer.Stop();
        frame->Destroy();
        ExitMainLoop();
    }
    void Run()
    {
        try
        {
            if (!supported)
            {
                Check(!frame->SetShape(Region()), "unsupported display accepts shape after realization");
                result = 0;
                std::puts("GTK4 unsupported-backend shape refusal PASS");
                Finish();
                return;
            }
#ifdef GDK_WINDOWING_X11
            if (step == 0)
            {
                CheckRegion();
                if (const char* expected = std::getenv("WX_SHAPE_EXPECT_SCALE"))
                    Check(gdk_surface_get_scale(Surface()) == std::atoi(expected),
                          "requested actual surface scale was not selected");
                Check(frame->SetShape(wxRegion()), "Clear rejected a supported surface");
                CheckClear();
                // Setting a region after realization must retain state for Clear
                // and for replacement of the native surface.
                Check(frame->SetShape(Region()), "post-realize region rejected");
                CheckRegion();
                frame->Hide();
                gtk_widget_unrealize(frame->m_widget);
                frame->Show();
            }
            else if (step == 1)
            {
                CheckRegion();
                wxGraphicsPath path = wxGraphicsRenderer::GetDefaultRenderer()->CreatePath();
                path.AddCircle(60, 60, 32);
                Check(frame->SetShape(path), "path shape rejected");
                frame->Refresh();
            }
            else
            {
                for (int kind : {ShapeBounding, ShapeInput})
                {
                    Check(Contains(kind, 60, 60), "path center was clipped");
                    Check(!Contains(kind, 10, 10), "path exterior was not clipped");
                }
                Check(frame->SetShape(wxRegion()), "path Clear failed");
                CheckClear();
                result = 0;
                std::puts("GTK4 X11 bounding/input, Clear, re-realize and path contracts PASS");
                Finish();
                return;
            }
            ++step;
#endif
        }
        catch (const std::exception& error)
        {
            std::fprintf(stderr, "%s\n", error.what());
            Finish();
        }
    }
public:
    bool OnInit() override
    {
        wxLog::SetActiveTarget(new wxLogStderr);
        frame = new wxFrame(NULL, wxID_ANY, "GTK4 shape contract", wxDefaultPosition,
                            wxSize(320, 220), wxFRAME_SHAPED | wxNO_BORDER);
#ifdef GDK_WINDOWING_X11
        GdkDisplay* display = gtk_widget_get_display(frame->m_widget);
        supported = GDK_IS_X11_DISPLAY(display) && gdk_display_supports_input_shapes(display);
#endif
        if (gtk_widget_get_realized(frame->m_widget) || frame->SetShape(Region()) != supported)
        {
            std::fprintf(stderr, "pre-realize shape/backend contract failed\n");
            delete frame;
            return false;
        }
        frame->Bind(wxEVT_PAINT, [this](wxPaintEvent&) {
            wxPaintDC dc(frame);
            dc.SetBackground(*wxRED_BRUSH);
            dc.Clear();
        });
        timer.SetOwner(this);
        Bind(wxEVT_TIMER, [this](wxTimerEvent&) { Run(); });
        frame->Show();
        timer.Start(500);
        return true;
    }
    int OnRun() override { wxApp::OnRun(); return result; }
};
wxIMPLEMENT_APP(ShapeContract);
