// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <algorithm>
#include <cstdio>
#include <stdexcept>
#include <vector>
#define __WXGTK20__ 1
#define __WXGTK3__ 1
#define __WXGTK4__ 1
#define WXUNUSED(x) x
#define wxMin(a,b) std::min(a,b)
static void Check(bool ok, const char* why) { if (!ok) throw std::runtime_error(why); }
struct GdkDevice {};
struct GdkSurface { bool toplevel = true; };
struct GtkRoot { bool native = true; GdkSurface* surface = nullptr; };
struct GtkWidget { GtkRoot* root = nullptr; };
enum GdkEventType { GDK_BUTTON_PRESS, GDK_BUTTON_RELEASE, GDK_TOUCH_BEGIN, GDK_TOUCH_UPDATE, GDK_MOTION_NOTIFY };
enum GdkSurfaceEdge { GDK_SURFACE_EDGE_SOUTH_WEST, GDK_SURFACE_EDGE_SOUTH_EAST };
struct GdkEvent {
    GdkEventType type = GDK_BUTTON_PRESS; unsigned button = 1;
    bool emulating = true, position = true;
    GdkDevice* device = nullptr; GdkSurface* surface = nullptr;
    double x = 10.25, y = 20.75; unsigned time = 12345;
};
GdkEvent* g_lastMouseEvent = nullptr;
struct Calls {
    int resize = 0, move = 0, translate = 0, buttonRead = 0, touchRead = 0;
    bool translationOK = true;
    GdkSurface* surface = nullptr; GdkDevice* device = nullptr;
    int button = 0; double x = 0, y = 0; unsigned time = 0;
    GdkSurfaceEdge edge = GDK_SURFACE_EDGE_SOUTH_EAST;
} calls;
#define GTK_IS_NATIVE(root) ((root)->native)
#define GTK_NATIVE(root) (root)
#define GDK_IS_TOPLEVEL(surface) ((surface)->toplevel)
#define GDK_TOPLEVEL(surface) (surface)
static GdkEventType gdk_event_get_event_type(GdkEvent* e) { Check(e, "null event type"); return e->type; }
static unsigned gdk_button_event_get_button(GdkEvent* e) { Check(e->type == GDK_BUTTON_PRESS, "button accessor on non-button event"); ++calls.buttonRead; return e->button; }
static bool gdk_touch_event_get_emulating_pointer(GdkEvent* e) { Check(e->type == GDK_TOUCH_BEGIN, "touch accessor on wrong event"); ++calls.touchRead; return e->emulating; }
static GtkRoot* gtk_widget_get_root(GtkWidget* w) { return w->root; }
static GdkSurface* gtk_native_get_surface(GtkRoot* r) { return r->surface; }
static GdkSurface* gdk_event_get_surface(GdkEvent* e) { return e->surface; }
static GdkDevice* gdk_event_get_device(GdkEvent* e) { return e->device; }
static bool gdk_event_get_position(GdkEvent* e, double* x, double* y) { *x=e->x; *y=e->y; return e->position; }
static unsigned gdk_event_get_time(GdkEvent* e) { return e->time; }
static bool gdk_surface_translate_coordinates(GdkSurface* from, GdkSurface* to, double* x, double* y) {
    Check(from != to, "same surface need not translate"); ++calls.translate;
    if (!calls.translationOK) return false;
    *x += 100.5; *y -= 3.25; return true;
}
static void Capture(GdkSurface* s, GdkDevice* d, int button, double x, double y, unsigned time) {
    calls.surface=s; calls.device=d; calls.button=button; calls.x=x; calls.y=y; calls.time=time;
}
static void gdk_toplevel_begin_resize(GdkSurface* s, GdkSurfaceEdge edge, GdkDevice* d, int button, double x, double y, unsigned time) {
    ++calls.resize; calls.edge=edge; Capture(s,d,button,x,y,time);
}
static void gdk_toplevel_begin_move(GdkSurface* s, GdkDevice* d, int button, double x, double y, unsigned time) {
    ++calls.move; Capture(s,d,button,x,y,time);
}
struct wxPoint { int x, y; };
struct wxRect {
    int x,y,width,height;
    wxRect(int X,int Y,int W,int H):x(X),y(Y),width(W),height(H){}
    int GetRight() const { return x+width-1; }
    int GetBottom() const { return y+height-1; }
    bool Contains(wxPoint p) const { return width>0 && height>0 && p.x>=x && p.x<=GetRight() && p.y>=y && p.y<=GetBottom(); }
};
enum { wxLayout_LeftToRight, wxLayout_RightToLeft, wxBRUSHSTYLE_TRANSPARENT };
struct wxMouseEvent { wxPoint point; bool skipped=false; wxPoint GetPosition() const { return point; } void Skip() { skipped=true; } };
struct wxPaintEvent {};
struct Font { bool IsOk() const { return false; } };
struct Lines { int pen; wxPoint a,b; };
static std::vector<Lines> drawn;
class wxDC {
    int pen=0;
public:
    void SetPen(int p) { pen=p; }
    void DrawLine(int x,int y,int X,int Y) { drawn.push_back({pen,{x,y},{X,Y}}); }
    void SetFont(Font) {}
    int GetCharHeight() const { return 12; }
    void SetBackgroundMode(int) {}
};
class wxStatusBarGeneric;
class wxPaintDC : public wxDC { public: explicit wxPaintDC(wxStatusBarGeneric*) {} };
class wxWindow {
public:
    int width=240,height=24;
    void DoGetClientSize(int* w,int* h) const { *w=width; *h=height; }
};
class wxStatusBarGeneric : public wxWindow {
public:
    GtkWidget* m_widget=nullptr; bool grip=true; int layout=wxLayout_LeftToRight, scale=1;
    int m_hilightPen=11,m_mediumShadowPen=22;
    struct Panes { size_t GetCount() const { return 0; } } m_panes;
    bool ShowsSizeGrip() const { return grip; }
    int GetLayoutDirection() const { return layout; }
    int FromDIP(int n) const { return n*scale; }
    Font GetFont() const { return {}; }
    void DrawField(wxDC&,int,int) {}
    wxRect GetSizeGripRect() const;
    void OnLeftDown(wxMouseEvent&);
    void OnRightDown(wxMouseEvent&);
    void OnPaint(wxPaintEvent&);
};

// PRODUCTION_FUNCTIONS

static void Exercise()
{
    GdkDevice device; GdkSurface top, child; GtkRoot root{true,&top}; GtkWidget widget{&root};
    GdkEvent native; native.device=&device; native.surface=&top;
    wxStatusBarGeneric bar; bar.m_widget=&widget;
    auto reset = [&] { calls={}; native={}; native.device=&device; native.surface=&top;
        root={true,&top}; widget.root=&root; top.toplevel=true; g_lastMouseEvent=&native;
        bar.grip=true; bar.layout=wxLayout_LeftToRight; };
    auto refused = [&] { wxMouseEvent event{{225,12}}; bar.OnLeftDown(event);
        Check(event.skipped && !calls.resize && !calls.move, "refused native state must skip"); };
    for (int missing=0; missing!=9; ++missing) {
        reset();
        switch(missing) {
            case 0:g_lastMouseEvent=nullptr;break;
            case 1:widget.root=nullptr;break;
            case 2:root.native=false;break;
            case 3:root.surface=nullptr;break;
            case 4:top.toplevel=false;break;
            case 5:native.surface=nullptr;break;
            case 6:native.device=nullptr;break;
            case 7:native.position=false;break;
            case 8:native.surface=&child;calls.translationOK=false;break;
        }
        refused();
    }
    for (GdkEventType type : {GDK_BUTTON_RELEASE,GDK_TOUCH_UPDATE,GDK_MOTION_NOTIFY}) { reset(); native.type=type; refused(); }
    reset();native.button=3;refused();
    reset();native.type=GDK_TOUCH_BEGIN;native.emulating=false;refused();
    for (bool rtl : {false,true}) for (bool translated : {false,true}) {
        reset();bar.layout=rtl?wxLayout_RightToLeft:wxLayout_LeftToRight;
        if (translated) native.surface=&child;
        wxMouseEvent event{{225,12}}; bar.OnLeftDown(event);
        Check(!event.skipped && calls.resize==1 && !calls.move, "valid grip resize");
        Check(calls.edge==(rtl?GDK_SURFACE_EDGE_SOUTH_WEST:GDK_SURFACE_EDGE_SOUTH_EAST), "physical RTL edge");
        Check(calls.surface==&top && calls.device==&device && calls.button==1 && calls.time==native.time, "native drag identity");
        Check(calls.x==native.x+(translated?100.5:0) && calls.y==native.y-(translated?3.25:0), "surface coordinates preserved/translated");
        Check(calls.translate==(translated?1:0) && g_lastMouseEvent==&native, "scope event remains owned by dispatcher");
    }
    reset();native.type=GDK_TOUCH_BEGIN; wxMouseEvent touch{{225,12}};bar.OnLeftDown(touch);
    Check(!touch.skipped && calls.resize==1 && calls.buttonRead==0 && calls.touchRead==1, "pointer-emulating touch resizes without button accessor");
    reset();native.button=3;wxMouseEvent right{{225,12}};bar.OnRightDown(right);
    Check(!right.skipped && calls.move==1 && !calls.resize && calls.button==3, "right click moves with actual button3");
    reset();native.type=GDK_TOUCH_BEGIN;wxMouseEvent wrongTouch{{225,12}};bar.OnRightDown(wrongTouch);
    Check(wrongTouch.skipped && !calls.move && calls.buttonRead==0, "touch cannot synthesize right move");
    reset();bar.grip=false;refused();
    for (wxPoint outside : {wxPoint{0,12},wxPoint{225,0},wxPoint{239,12},wxPoint{225,23}}) {
        reset();wxMouseEvent event{outside};bar.OnLeftDown(event);Check(event.skipped && !calls.resize,"outside actual grip must skip");
    }
    for (bool rtl : {false,true}) for (int scale : {1,2}) for (int height : {2,4,24}) {
        reset();bar.layout=rtl?wxLayout_RightToLeft:wxLayout_LeftToRight;bar.scale=scale;bar.height=height;
        drawn.clear();wxPaintEvent paint;bar.OnPaint(paint);
        const wxRect rc=bar.GetSizeGripRect();
        Check(rc.x==bar.width-height-2, "both layouts use logical-right grip");
        if (height==24) Check(!drawn.empty(), "normal grip draws lines");
        else Check(drawn.empty(), "tiny grip does not draw outside its area");
        Check(drawn.size()%2==0,"paired theme strokes");
        for (size_t i=0;i<drawn.size();++i) {
            Check(rc.Contains(drawn[i].a)&&rc.Contains(drawn[i].b),"line endpoints inside grip");
            Check(drawn[i].pen==(i%2?bar.m_mediumShadowPen:bar.m_hilightPen),"theme pen order");
        }
    }
    reset();bar.grip=false;drawn.clear();wxPaintEvent paint;bar.OnPaint(paint);Check(drawn.empty(),"disabled grip not drawn");
}
int main()
{
    try { Exercise(); }
    catch(const std::exception& error) { std::fprintf(stderr,"%s\n",error.what());return 1; }
    std::puts("PASS: actual GTK4 statusbar drag, hit-test and logical grip drawing contracts");
}
