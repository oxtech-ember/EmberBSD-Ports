// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD contributors (AI-assisted).
#include <glib-object.h>
#include <memory>
#include <cstring>
#include <thread>
#include <vector>
#include <cstdio>
#include <cstdlib>
static void Check(bool ok, const char* why) {
    if (!ok) { std::fprintf(stderr,"FAIL: %s\n",why); std::abort(); }
}
#define wxASSERT(x) Check(x,#x)
static std::thread::id ui;
using GtkWidget = GObject;
using GdkTexture = GObject;
#define GTK_WIDGET(x) ((GtkWidget*)(x))
struct graphene_rect_t { float x,y,width,height; };
#define GRAPHENE_RECT_INIT(x,y,w,h) graphene_rect_t{x,y,w,h}
struct GdkRGBA { float r,g,b,a; };
struct GtkSnapshot { int colors=0,textures=0; graphene_rect_t bounds{}; };
static int textures=0,draws=0;
static void Ui() { Check(std::this_thread::get_id()==ui,"GTK resource used off UI thread"); }
static void TextureDead(gpointer,GObject*) { Ui(); --textures; }
enum { GDK_MEMORY_R8G8B8A8 };
static GdkTexture* gdk_memory_texture_new(int w,int h,int format,GBytes* bytes,size_t stride) {
    Ui();Check(format==GDK_MEMORY_R8G8B8A8 && stride==size_t(w)*4,"texture pixel contract");
    Check(g_bytes_get_size(bytes)==stride*h,"texture bytes extent");
    GObject* texture=G_OBJECT(g_object_new(G_TYPE_OBJECT,nullptr));
    g_object_set_data_full(texture,"bytes",g_bytes_ref(bytes),(GDestroyNotify)g_bytes_unref);
    g_object_weak_ref(texture,TextureDead,nullptr);++textures;return texture;
}
static int gtk_widget_get_width(GtkWidget*) { Ui();return 200; }
static int gtk_widget_get_height(GtkWidget*) { Ui();return 100; }
static void gtk_widget_queue_draw(GtkWidget*) { Ui();++draws; }
static void gtk_snapshot_append_color(GtkSnapshot* s,const GdkRGBA* color,const graphene_rect_t*) {
    Ui();Check(color->a==1 && color->r==0,"black letterbox");++s->colors;
}
static void gtk_snapshot_append_texture(GtkSnapshot* s,GdkTexture*,const graphene_rect_t* rect) {
    Ui();++s->textures;s->bounds=*rect;
}
// The GStreamer boundary supplies format/stride metadata exactly as the sample
// APIs do. Mapping/unmapping/ref balancing is checked, decoding is not mocked.
enum GstFlowReturn { GST_FLOW_OK,GST_FLOW_FLUSHING,GST_FLOW_ERROR };
enum { GST_VIDEO_FORMAT_RGBA,GST_MAP_READ };
struct GstVideoInfo { int width=0,height=0,par_n=1,par_d=1,format=GST_VIDEO_FORMAT_RGBA; };
struct GstCaps { GstVideoInfo info; bool valid=true; };
struct GstBuffer { std::vector<guchar> bytes; int stride=12; size_t offset=0; bool valid=true; };
struct GstSample { GstCaps caps; GstBuffer buffer; int refs=1; };
struct GstElement { GstSample* sample=nullptr; const char* action=nullptr; };
struct GstMapInfo { guchar* data; gsize size; };
struct GstVideoFrame { GstBuffer* buffer; GstMapInfo map[1]; };
static int maps=0,samples=0;
static void wxTestPull(GstElement* sink,const char* action,GstSample** out) {
    Check(std::strcmp(action,"pull-sample")==0 || std::strcmp(action,"pull-preroll")==0,"public sample action");
    sink->action=action;*out=sink->sample;sink->sample=nullptr;
}
#define g_signal_emit_by_name wxTestPull
static void gst_video_info_init(GstVideoInfo* info) { *info={}; }
static GstCaps* gst_sample_get_caps(GstSample* s) { return &s->caps; }
static GstBuffer* gst_sample_get_buffer(GstSample* s) { return &s->buffer; }
static bool gst_video_info_from_caps(GstVideoInfo* i,GstCaps* c) { *i=c->info;return c->valid; }
#define GST_VIDEO_INFO_FORMAT(i) ((i)->format)
static bool gst_video_frame_map(GstVideoFrame* f,GstVideoInfo*,GstBuffer* b,int) {
    if (!b->valid) return false;
    f->buffer=b;f->map[0]={b->bytes.data(),b->bytes.size()};++maps;return true;
}
#define GST_VIDEO_FRAME_PLANE_STRIDE(f,p) ((f)->buffer->stride)
#define GST_VIDEO_FRAME_PLANE_DATA(f,p) ((f)->buffer->bytes.data()+(f)->buffer->offset)
static void gst_video_frame_unmap(GstVideoFrame*) { --maps; }
static void gst_sample_unref(GstSample* s) { Check(--s->refs==0,"sample full ownership");--samples;delete s; }

// PRODUCTION_MEDIA_PRESENTATION

static GstSample* Sample(int value) {
    auto s=new GstSample; ++samples;s->caps.info.width=2;s->caps.info.height=2;
    s->buffer.bytes.assign(24,0xee);
    for(int y=0;y<2;++y) for(int x=0;x<8;++x) s->buffer.bytes[y*12+x]=guchar(value);
    return s;
}
static void Drain(GMainContext* context) { while(g_main_context_iteration(context,FALSE)) {} }
static void Exercise() {
    ui=std::this_thread::get_id();
    GMainContext* context=g_main_context_new();g_main_context_push_thread_default(context);
    GtkWidget* widget=G_OBJECT(g_object_new(G_TYPE_OBJECT,nullptr));
    auto state=std::make_shared<wxGTKMediaPresentation>(widget);
    auto closure=new wxGTKMediaPresentationPtr(state);
    // Queue from a streaming thread: even an otherwise idle context must not
    // run GTK inline, and replacing the latest frame must not grow a queue.
    std::thread producer([&] {
        for(int value=1;value<=3;++value) {
            GstElement sink{Sample(value)};
            Check(wxGTKMediaNewSample(&sink,closure)==GST_FLOW_OK,"sample accepted");
        }
    });producer.join();
    Check(!textures && !draws && state->source,"delivery remains queued on UI");
    Check(samples==0 && maps==0,"samples and mapped buffers released before UI");
    Check(g_bytes_get_size(state->pending->bytes)==16,"padding excluded from packed RGBA");
    const auto pixels=static_cast<const guchar*>(g_bytes_get_data(state->pending->bytes,nullptr));
    for(int i=0;i<16;++i) Check(pixels[i]==3,"latest frame contents and row stride");
    Drain(context);Check(textures==1 && draws==1 && !state->source && !state->pending,"single latest frame delivered");
    GtkSnapshot snapshot;wxGTKMediaSnapshot(widget,&snapshot,closure);
    Check(snapshot.colors==1 && snapshot.textures==1 && snapshot.bounds.x==50 && snapshot.bounds.width==100,"aspect-preserving snapshot");
    GstElement preroll{Sample(4)};
    preroll.sample->buffer.bytes.insert(preroll.sample->buffer.bytes.begin(), 4, 0xee);
    preroll.sample->buffer.offset=4;
    Check(wxGTKMediaNewPreroll(&preroll,closure)==GST_FLOW_OK && std::strcmp(preroll.action,"pull-preroll")==0,"paused preroll consumed");
    // Destruction before dispatch cancels pending delivery and releases the
    // UI texture there; a late streaming callback sees only detached state.
    state->Detach();Check(textures==0 && !state->pending && !state->source,"detach releases resources");
    Drain(context);Check(draws==1,"cancelled delivery never touches widget");
    std::thread late([&] {
        GstElement sink{Sample(5)};Check(wxGTKMediaNewSample(&sink,closure)==GST_FLOW_OK,"late frame safely discarded");
    });late.join();Check(!state->source && !state->pending,"detached state cannot reschedule");
    wxGTKMediaDeleteClosure(closure,nullptr);state.reset();g_object_unref(widget);
    // If native widget disposal precedes backend teardown, weak acquisition
    // fails and delivery never creates a texture or draws into freed memory.
    widget=G_OBJECT(g_object_new(G_TYPE_OBJECT,nullptr));
    state=std::make_shared<wxGTKMediaPresentation>(widget);closure=new wxGTKMediaPresentationPtr(state);
    GstElement orphan{Sample(6)};Check(wxGTKMediaNewSample(&orphan,closure)==GST_FLOW_OK,"orphan queued");
    g_object_unref(widget);Drain(context);Check(textures==0 && draws==1,"destroyed native widget not accessed");
    for(int kind=0;kind<8;++kind) {
        auto sample=Sample(7);
        if(kind==0) sample->caps.valid=false;
        if(kind==1) sample->caps.info.format=999;
        if(kind==2) sample->buffer.valid=false;
        if(kind==3) sample->buffer.stride=4;
        if(kind==4) sample->caps.info.height=0;
        if(kind==5) sample->buffer.bytes.resize(10); // second row truncated
        if(kind==6) sample->buffer.stride=G_MAXINT; // positive stride exceeds mapping
        if(kind==7) sample->buffer.offset=24; // one-past plane start, no visible bytes
        GstElement bad{sample};Check(wxGTKMediaNewSample(&bad,closure)==GST_FLOW_ERROR,"invalid frame refuses");
        Check(samples==0 && maps==0,"invalid sample cleanup");
    }
    GstElement empty;Check(wxGTKMediaNewSample(&empty,closure)==GST_FLOW_FLUSHING,"empty/flushing sample");
    state->Detach();wxGTKMediaDeleteClosure(closure,nullptr);state.reset();
    Check(!g_main_context_pending(context) && !samples && !maps && !textures,"all resources released");
    g_main_context_pop_thread_default(context);g_main_context_unref(context);
}
int main() { Exercise();std::puts("PASS: actual media frame stride/mailbox/UI dispatch/shutdown/snapshot contracts"); }
