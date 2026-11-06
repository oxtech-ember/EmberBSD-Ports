// Origin: EmberBSD (AI-assisted). SPDX-License-Identifier: BSD-2-Clause
// Compile the actual patched src/gtk/win_gtk.cpp with the configured wx/GTK4
// SDK flags. This test exercises GTK's allocation and snapshot machinery.
#include "wx/defs.h"
#include <gtk/gtk.h>
#include "wx/gtk/private/win_gtk.h"
#include <cstdio>
#include <cmath>
#include <stdexcept>

#ifndef __WXGTK4__
#error This test requires the actual GTK4 wxWidgets configuration.
#endif

static void Check(bool condition, const char* message)
{
    if (!condition)
        throw std::runtime_error(message);
}

static void Flush()
{
    while (g_main_context_pending(NULL))
        g_main_context_iteration(NULL, false);
}

static void FramePainted(GdkFrameClock*, bool* painted) { *painted = true; }

static void Redraw(GtkWidget* widget)
{
    GdkFrameClock* clock = gtk_widget_get_frame_clock(widget);
    bool painted = false;
    const gulong id = g_signal_connect_after(clock, "after-paint", G_CALLBACK(FramePainted), &painted);
    gtk_widget_queue_draw(widget);
    const gint64 deadline = g_get_monotonic_time() + 3000000;
    while (!painted && g_get_monotonic_time() < deadline)
    {
        Flush();
        g_usleep(1000);
    }
    g_signal_handler_disconnect(clock, id);
    Check(painted, "requested frame did not complete");
}

static void CheckPosition(GtkWidget* parent, GtkWidget* child, float x, float y)
{
    graphene_point_t origin, position;
    graphene_point_init(&origin, 0, 0);
    Check(gtk_widget_compute_point(child, parent, &origin, &position), "child coordinate transform");
    Check(std::fabs(position.x - x) < 0.01 && std::fabs(position.y - y) < 0.01,
          "child position, scrolling or RTL mismatch");
}

static void Paint(GtkWidget*, cairo_t* cr, unsigned* paints)
{
    ++*paints;
    cairo_set_source_rgb(cr, 0.75, 0.1, 0.2);
    cairo_paint(cr);
}

static void UnparentOnNotify(GtkWidget* child, GParamSpec*, void*)
{
    if (gtk_widget_get_parent(child))
        gtk_widget_unparent(child);
}

struct Allocations { unsigned count = 0; bool valid = true; };

static void Allocated(GtkWidget* widget, int width, int height, Allocations* allocations)
{
    allocations->valid &= width == gtk_widget_get_width(widget) && height == gtk_widget_get_height(widget);
    ++allocations->count;
}

int main()
{
    if (!gtk_init_check())
    {
        std::fputs("GTK4 display unavailable; runtime contract was not executed\n", stderr);
        return 2;
    }
    GtkWidget* window = gtk_window_new();
    GtkWidget* child = NULL;
    g_object_ref(window);
    try
    {
        GtkWidget* widget = wxPizza::New(wxBORDER_SIMPLE);
        wxPizza* pizza = WX_PIZZA(widget);
        gtk_window_set_child(GTK_WINDOW(window), widget);
        gtk_window_set_default_size(GTK_WINDOW(window), 320, 240);
        child = gtk_drawing_area_new();
        g_object_ref_sink(child);
        pizza->put(child, 10, 20, 40, 30);
        unsigned paints = 0;
        Allocations allocations;
        g_signal_connect(widget, "wx-paint", G_CALLBACK(Paint), &paints);
        g_signal_connect(widget, "wx-size-allocate", G_CALLBACK(Allocated), &allocations);
        gtk_window_present(GTK_WINDOW(window));

        const gint64 deadline = g_get_monotonic_time() + 3000000;
        while ((!gtk_widget_get_mapped(widget) || !paints) && g_get_monotonic_time() < deadline)
        {
            Flush();
            g_usleep(1000);
        }
        Check(gtk_widget_get_mapped(widget) && paints, "widget did not allocate and paint");
        Check(allocations.count != 0 && allocations.valid,
              "wx allocation notification must report GTK content dimensions");
        CheckPosition(widget, child, 10, 20);
        Check(gtk_widget_get_width(child) == 40 && gtk_widget_get_height(child) == 30,
              "wx child size was not preserved");
        GtkBorder border;
        pizza->get_border(border);
        Check(border.left == 1 && border.right == 1 && border.top == 1 && border.bottom == 1,
              "simple border contract");

        const unsigned beforeFreeze = paints;
        g_object_set_data(G_OBJECT(widget), "wx-frozen", GINT_TO_POINTER(1));
        Redraw(widget);
        Check(paints == beforeFreeze, "frozen widget repainted instead of retaining its snapshot");
        g_object_set_data(G_OBJECT(widget), "wx-frozen", NULL);
        Redraw(widget);
        Check(paints > beforeFreeze, "thawed widget did not repaint");

        // Outside-paint drawing must preserve the native renderer and must
        // not be erased by an extra wxPaint triggered by its own queue_draw.
        void* dcToken = NULL;
        cairo_t* dc = pizza->BeginClientDC(&dcToken);
        Check(dc && dcToken, "could not acquire real client content for DC");
        cairo_set_source_rgb(dc, 0, 0, 1);
        cairo_paint(dc);
        cairo_destroy(dc);
        const unsigned beforeDC = paints;
        wxPizza::EndClientDC(dcToken);
        Redraw(widget);
        Check(paints == beforeDC, "ClientDC was overwritten by its own paint event");
        GtkNative* native = gtk_widget_get_native(widget);
        graphene_rect_t sample = GRAPHENE_RECT_INIT(0, 0, 1, 1);
        GdkTexture* pixel = gsk_renderer_render_texture(gtk_native_get_renderer(native),
                                                       pizza->m_contentSnapshot, &sample);
        unsigned char rgba[4] = {};
        gdk_texture_download(pixel, rgba, 4);
        g_object_unref(pixel);
#if G_BYTE_ORDER == G_LITTLE_ENDIAN
        Check(rgba[0] == 255 && rgba[2] == 0 && rgba[3] == 255, "ClientDC pixels did not reach retained content");
#else
        Check(rgba[0] == 255 && rgba[1] == 0 && rgba[3] == 255, "ClientDC pixels did not reach retained content");
#endif
        pizza->InvalidateClientDC();
        Redraw(widget);
        Check(paints > beforeDC, "Refresh did not restore ordinary painting after ClientDC");

        GtkWidget* transient = gtk_drawing_area_new();
        g_object_ref_sink(transient);
        const gulong unparent = g_signal_connect(transient, "notify::parent",
            G_CALLBACK(UnparentOnNotify), NULL);
        pizza->put(transient, 1, 1, 10, 10);
        Check(!gtk_widget_get_parent(transient) && g_list_length(pizza->m_children) == 1,
              "reentrant parent notification left a stale child record");
        g_signal_handler_disconnect(transient, unparent);
        g_object_unref(transient);

        pizza->set_virtual_size(1000, 800);
        int minimum, natural;
        gtk_widget_measure(widget, GTK_ORIENTATION_HORIZONTAL, -1,
                           &minimum, &natural, NULL, NULL);
        Check(minimum < 320 && natural >= 1000, "virtual extent prevents viewport shrinking");

        pizza->scroll(-5, -7);
        gtk_widget_allocate(widget, 320, 240, -1, NULL);
        CheckPosition(widget, child, 5, 13);

        gtk_widget_set_direction(widget, GTK_TEXT_DIR_RTL);
        gtk_widget_allocate(widget, 320, 240, -1, NULL);
        CheckPosition(widget, child, gtk_widget_get_width(widget) - 5 - 40, 13);

        pizza->move(child, 30, 40, 60, 20);
        gtk_widget_allocate(widget, 320, 240, -1, NULL);
        CheckPosition(widget, child, gtk_widget_get_width(widget) - 25 - 60, 33);

        // Removing externally must remove the coordinate record too, even
        // while another owner still holds a reference to the child widget.
        gtk_widget_unparent(child);
        Check(pizza->m_children == NULL, "external unparent left a stale child record");
        pizza->put(child, 1, 2, 20, 10);
        gtk_window_destroy(GTK_WINDOW(window));
        g_object_unref(window);
        window = NULL;
        Flush();
        Check(gtk_widget_get_parent(child) == NULL, "container disposal retained its child");
        g_object_unref(child);
        child = NULL;
        std::puts("GTK4 wxPizza allocation, border, snapshot, scroll, RTL and ownership PASS");
        return 0;
    }
    catch (const std::exception& error)
    {
        std::fprintf(stderr, "%s\n", error.what());
        if (window)
        {
            gtk_window_destroy(GTK_WINDOW(window));
            g_object_unref(window);
        }
        if (child)
            g_object_unref(child);
        return 1;
    }
}
