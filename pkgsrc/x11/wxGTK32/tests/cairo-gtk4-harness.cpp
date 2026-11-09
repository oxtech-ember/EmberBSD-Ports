// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <cairo.h>
#include <pango/pangocairo.h>
#include <glib-object.h>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#define __WXGTK4__ 1
#define __WXGTK3__ 1
#define __WXGTK__ 1
static void Check(bool ok,const char* why) { if(!ok) {std::fprintf(stderr,"FAIL: %s\n",why);std::abort();} }
#define wxASSERT(x) Check(x,#x)
#define wxASSERT_MSG(x,msg) Check(x,msg)
#define wxS(x) x
#define wxDECLARE_NO_COPY_CLASS(c) c(const c&)=delete; c& operator=(const c&)=delete
#define wxDECLARE_NO_COPY_TEMPLATE_CLASS(c,t) wxDECLARE_NO_COPY_CLASS(c)
#define wxCHECKED_DELETE(p) delete p
#define ENSURE_LOADED_OR_RETURN(x) do {} while(0)
static int refused=0;
#define wxFAIL_MSG(x) do { ++refused; } while(0)
// PRODUCTION_GTK_OBJECT
// PRODUCTION_SCOPED_PTR

class wxWindow;
struct GtkWidget { wxWindow* owner=nullptr; };
using GtkNative=GtkWidget;
#define GTK_WIDGET(x) (x)
struct GdkSurface { int width=200,height=100; bool destroyed=false,failCreate=false,failBegin=false,failCairo=false; GtkNative* native=nullptr; };
using GdkCairoContext=GObject;
#define GDK_DRAW_CONTEXT(x) (x)
static int created=0,begun=0,ended=0,released=0,crAlive=0,dcAlive=0;
struct Frame { GdkSurface* surface; bool in=false; bool cairo=false; };
static Frame* FrameOf(GObject* o) {return static_cast<Frame*>(g_object_get_data(o,"frame"));}
static void FrameDelete(gpointer p) { auto f=static_cast<Frame*>(p);Check(!f->in&&!f->cairo,"native unref after end and Cairo destruction");++released;delete f; }
static int gdk_surface_get_width(GdkSurface* s) {return s->width;}
static int gdk_surface_get_height(GdkSurface* s) {return s->height;}
static bool gdk_surface_is_destroyed(GdkSurface* s) {return s->destroyed;}
static GtkNative* gtk_native_get_for_surface(GdkSurface* s) {return s->native;}
static GdkCairoContext* gdk_surface_create_cairo_context(GdkSurface* s) {
    Check(!s->native,"must not detach GTK renderer");
    if(s->failCreate)return nullptr;
    auto o=G_OBJECT(g_object_new(G_TYPE_OBJECT,nullptr));++created;
    g_object_set_data_full(o,"frame",new Frame{s},FrameDelete);return o;
}
static void gdk_draw_context_begin_frame(GObject* o,cairo_region_t* region) {
    auto f=FrameOf(o);cairo_rectangle_int_t r;cairo_region_get_extents(region,&r);
    Check(r.width==f->surface->width&&r.height==f->surface->height,"frame extent");
    if(!f->surface->failBegin) {Check(!f->in,"begin once");f->in=true;++begun;}
}
static bool gdk_draw_context_is_in_frame(GObject* o) {return FrameOf(o)->in;}
static void gdk_draw_context_end_frame(GObject* o) {
    auto f=FrameOf(o);Check(f->in&&!f->cairo,"Cairo destroyed before end frame");f->in=false;++ended;
}
static cairo_user_data_key_t rawKey;
static void CairoGone(void* p) {auto f=static_cast<Frame*>(p);Check(f->in,"Cairo stays within frame");f->cairo=false;--crAlive;}
static cairo_t* ImageContext(int w,int h) {
    auto surface=cairo_image_surface_create(CAIRO_FORMAT_ARGB32,w,h);
    auto cr=cairo_create(surface);cairo_surface_destroy(surface);return cr;
}
static cairo_t* gdk_cairo_context_cairo_create(GObject* o) {
    auto f=FrameOf(o);Check(f->in,"create inside frame");if(f->surface->failCairo)return nullptr;
    auto cr=ImageContext(f->surface->width,f->surface->height);f->cairo=true;++crAlive;
    Check(cairo_set_user_data(cr,&rawKey,f,CairoGone)==CAIRO_STATUS_SUCCESS,"Cairo lifetime marker");return cr;
}
struct wxSize {int x,y;};
class wxWindow {
public:
    GtkWidget* m_wxwindow=nullptr;wxWindow* parent=nullptr;bool dcAvailable=true;
    wxWindow* GetParent() {return parent;}
    wxSize GetClientSize() {return {80,40};}
};
static wxWindow* lastDCWindow=nullptr;
static wxWindow* wxWindowFromGtkWidget(GtkWidget* widget) {return widget->owner;}
class wxClientDC {
    cairo_t* cr;
public:
    explicit wxClientDC(wxWindow* w):cr(w->dcAvailable?ImageContext(80,40):nullptr) {++dcAlive;lastDCWindow=w;}
    ~wxClientDC() {if(cr){Check(cairo_get_reference_count(cr)==1,"graphics ref released before held DC");cairo_destroy(cr);}--dcAlive;}
    wxClientDC* GetImpl() {return this;}
    void* GetCairoContext() {return cr;}
};
static double contextDPI=144;
static bool nullPango=false;
static int pangoAlive=0;
static void PangoGone(gpointer,GObject*) {--pangoAlive;}
static PangoContext* wxGetPangoContext() {
    if(nullPango)return nullptr;
    auto p=pango_font_map_create_context(pango_cairo_font_map_get_default());
    pango_cairo_context_set_resolution(p,contextDPI);++pangoAlive;g_object_weak_ref(G_OBJECT(p),PangoGone,nullptr);return p;
}
class wxGraphicsRenderer {};
class wxGraphicsContext {
public:
    explicit wxGraphicsContext(wxGraphicsRenderer*,wxWindow* =nullptr){}
    virtual ~wxGraphicsContext(){}
    virtual void* GetNativeContext() const=0;
    void EnableOffset(){}
};
class wxCairoContext:public wxGraphicsContext {
    wxScopedPtr<wxClientDC> m_gtk4DC;
    wxGtkObject<GdkCairoContext> m_gtk4Native;
    cairo_t* m_context;
    cairo_matrix_t m_internalTransform;
public:
    double m_width=0,m_height=0;float m_fontScalingFactor=0;
    wxCairoContext(wxGraphicsRenderer*,GdkSurface*);
    wxCairoContext(wxGraphicsRenderer*,wxWindow*);
    wxCairoContext(wxGraphicsRenderer*,cairo_t*);
    ~wxCairoContext();
    void Init(cairo_t*);void PushState();void PopState();
    void* GetNativeContext() const override {return m_context;}
};
class wxCairoRenderer:public wxGraphicsRenderer {
public:wxGraphicsContext* CreateContextFromNativeWindow(void*);wxGraphicsContext* CreateMeasuringContext();
};
// PRODUCTION_METHODS

static void Exercise() {
    wxCairoRenderer renderer;GdkSurface surface;
    auto gc=renderer.CreateContextFromNativeWindow(&surface);
    Check(gc&&begun==1&&ended==0&&crAlive==1,"raw frame remains open during context lifetime");
    auto cr=static_cast<cairo_t*>(gc->GetNativeContext());
    cairo_set_source_rgb(cr,1,0,0);cairo_paint(cr);Check(cairo_status(cr)==CAIRO_STATUS_SUCCESS,"real Cairo drawing");
    delete gc;Check(begun==ended&&created==released&&crAlive==0,"raw frame resources balanced");
    for(int failure=0;failure<6;++failure) {
        GdkSurface bad;
        if(failure==0)bad.destroyed=true;
        if(failure==1)bad.width=0;
        if(failure==2)bad.height=0;
        if(failure==3)bad.failCreate=true;
        if(failure==4)bad.failBegin=true;
        if(failure==5)bad.failCairo=true;
        Check(!renderer.CreateContextFromNativeWindow(&bad),"invalid native context refuses");
        Check(begun==ended&&created==released&&!crAlive,"failed frame cleanup");
    }
    Check(!renderer.CreateContextFromNativeWindow(nullptr),"null surface refuses");
    GtkWidget widget;wxWindow owner;owner.m_wxwindow=&widget;widget.owner=&owner;surface.native=&widget;
    const int before=created;
    gc=renderer.CreateContextFromNativeWindow(&surface);
    Check(gc&&created==before&&dcAlive==1&&lastDCWindow==&owner,"wx native uses held common DC");
    Check(cairo_get_reference_count(static_cast<cairo_t*>(gc->GetNativeContext()))==2,"graphics retains Cairo alongside DC");
    delete gc;Check(dcAlive==0,"held DC released after graphics context");
    wxWindow child;child.parent=&owner;widget.owner=&child;
    gc=renderer.CreateContextFromNativeWindow(&surface);Check(gc&&lastDCWindow==&owner,"native controls retain parent fallback");delete gc;
    widget.owner=nullptr;Check(!renderer.CreateContextFromNativeWindow(&surface)&&refused==1&&created==before,"foreign GTK never creates raw frame");
    widget.owner=&owner;owner.dcAvailable=false;
    Check(!renderer.CreateContextFromNativeWindow(&surface)&&dcAlive==0,"failed shared DC refuses cleanly");
    const double previous=pango_cairo_font_map_get_resolution(PANGO_CAIRO_FONT_MAP(pango_cairo_font_map_get_default()));
    for(int test=0;test<3;++test) {
        contextDPI=test==0?192:-1;nullPango=test==2;
        pango_cairo_font_map_set_resolution(PANGO_CAIRO_FONT_MAP(pango_cairo_font_map_get_default()),test==2?96:144);
        auto measure=static_cast<wxCairoContext*>(renderer.CreateMeasuringContext());
        Check(measure&&created==before&&!dcAlive,"measurement without native surface or DC");
        Check(std::fabs(measure->m_fontScalingFactor-(test==0?2.0:test==1?1.5:1.0))<0.001,"context/default Pango DPI");
        auto target=cairo_get_target(static_cast<cairo_t*>(measure->GetNativeContext()));
        Check(cairo_image_surface_get_width(target)==1&&cairo_image_surface_get_height(target)==1,"1x1 measuring image");
        delete measure;Check(pangoAlive==0,"Pango context reference released");
    }
    pango_cairo_font_map_set_resolution(PANGO_CAIRO_FONT_MAP(pango_cairo_font_map_get_default()),previous);
    Check(created==released&&begun==ended&&!dcAlive&&!crAlive&&!pangoAlive,"final resources balanced");
}
int main(){Exercise();std::puts("PASS: actual Cairo GTK4 routing/frame/DC/measurement/DPI lifetimes");}
