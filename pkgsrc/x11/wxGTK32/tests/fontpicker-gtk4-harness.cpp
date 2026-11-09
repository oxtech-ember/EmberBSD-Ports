/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD contributors (AI-assisted). */
#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
using gpointer=void*;
class wxFontButton;
struct GObject; struct GtkWidget; struct GtkFontDialog; struct GAsyncResult;
struct GError { int code; };
using GWeakNotify=void(*)(gpointer,GObject*);
using GAsyncReadyCallback=void(*)(GObject*,GAsyncResult*,gpointer);
struct WeakNotify { GWeakNotify fn; gpointer data; };
struct GObject { std::unordered_map<std::string,void*> data; std::vector<WeakNotify> weak; bool alive=true; };
struct GtkWidget: GObject { GtkWidget* child=nullptr; std::string label; std::string attrs; wxFontButton* owner=nullptr; int refs=1; };
struct GtkFontDialog: GObject {};
struct GtkRoot: GObject {};
struct GtkWindow: GtkWidget {};
struct GWeakRef { GObject* object=nullptr; };
struct GCancellable { bool cancelled=false; };
struct PangoFontDescription { std::string text; };
struct PangoAttrList { std::string desc; };
struct GAsyncResult { bool success=false; std::string selected; };
#define G_OBJECT(x) ((GObject*)(x))
#define GTK_WIDGET(x) ((GtkWidget*)(x))
#define GTK_BUTTON(x) ((GtkWidget*)(x))
#define GTK_LABEL(x) ((GtkWidget*)(x))
#define GTK_FONT_DIALOG(x) ((GtkFontDialog*)(x))
#define GTK_IS_WINDOW(x) false
#define GTK_WINDOW(x) ((GtkWindow*)(x))
#define wxASSERT_MSG(c,m) assert(c)
#define wxGTK_CONV(x) ((x).c_str())
static constexpr long wxFNTP_FONTDESC_AS_LABEL=0x8, wxFNTP_USEFONT_FOR_LABEL=0x10;
static bool destroy_on_label=false;
static bool detach_label_on_text=false;
static bool check_label_ref=false;
static GtkWidget* gtk_button_get_child(GtkWidget* w) { return w->child; }
static GtkWidget* g_object_ref(GtkWidget* w) { ++w->refs; return w; }
static void g_object_unref(GtkWidget* w) { --w->refs; }
static void g_object_unref(GtkFontDialog*) {}
static void g_object_unref(GCancellable* c) { delete c; }
static void g_object_weak_ref(GObject* o,GWeakNotify fn,gpointer d) { o->weak.push_back({fn,d}); }
static void g_object_weak_unref(GObject* o,GWeakNotify fn,gpointer d) { o->weak.erase(std::remove_if(o->weak.begin(),o->weak.end(),[&](auto n){return n.fn==fn&&n.data==d;}),o->weak.end()); }
static void g_object_set_data(GObject* o,const char* k,gpointer d) { if(d)o->data[k]=d; else o->data.erase(k); }
static gpointer g_object_get_data(GObject* o,const char* k) { auto i=o->data.find(k); return i==o->data.end()?nullptr:i->second; }
static void g_weak_ref_init(GWeakRef* r,GObject* o) { r->object=o; }
static void g_weak_ref_clear(GWeakRef* r) { r->object=nullptr; }
static GObject* g_weak_ref_get(GWeakRef* r) { if(!r->object||!r->object->alive)return nullptr;auto* w=static_cast<GtkWidget*>(r->object);++w->refs;return w; }
static GCancellable* g_cancellable_new() { return new GCancellable; }
static void g_cancellable_cancel(GCancellable* c) { c->cancelled=true; }
static GtkFontDialog* gtk_font_dialog_new() { static GtkFontDialog d; return &d; }
static GAsyncReadyCallback pending_callback=nullptr;
static gpointer pending_data=nullptr;
static GCancellable* pending_cancel=nullptr;
static int open_count=0;
static void gtk_font_dialog_choose_font(GtkFontDialog*,GtkWindow*,PangoFontDescription*,GCancellable* c,GAsyncReadyCallback cb,gpointer d) { ++open_count; pending_callback=cb; pending_data=d; pending_cancel=c; }
static PangoFontDescription* gtk_font_dialog_choose_font_finish(GtkFontDialog*,GAsyncResult* r,GError** e) { if(!r->success||pending_cancel->cancelled){*e=new GError{1};return nullptr;}return new PangoFontDescription{r->selected}; }
static char* pango_font_description_to_string(PangoFontDescription* d) { return strdup(d->text.c_str()); }
static void pango_font_description_free(PangoFontDescription* d) { delete d; }
static void g_free(void* p) { free(p); }
static void g_clear_error(GError** e) { delete *e; *e=nullptr; }
static PangoAttrList* pango_attr_list_new() { return new PangoAttrList; }
static void pango_attr_list_insert(PangoAttrList* a,PangoAttrList* d) { a->desc=d->desc; delete d; }
static PangoAttrList* pango_attr_font_desc_new(PangoFontDescription* d) { return new PangoAttrList{d->text}; }
static void pango_attr_list_unref(PangoAttrList* a) { delete a; }
static void mock_delete_control(wxFontButton*);
static GtkWidget* mock_control_widget(wxFontButton*);
static void gtk_label_set_text(GtkWidget* w,const char* s) { w->label=s; if(detach_label_on_text&&w->owner){auto* parent=mock_control_widget(w->owner);assert(parent->child==w);parent->child=nullptr;--w->refs;detach_label_on_text=false;} if(destroy_on_label && w->owner){auto* p=w->owner;destroy_on_label=false;mock_delete_control(p);} }
static void gtk_label_set_attributes(GtkWidget* w,PangoAttrList* a) { if(check_label_ref)assert(w->refs>=2);w->attrs=a?a->desc:""; }

struct wxString { std::string s; wxString()=default; wxString(std::string x):s(std::move(x)){} static wxString FromUTF8(const char* x){return wxString(x?x:"");} const char* c_str()const{return s.c_str();} wxString& operator+=(const wxString& x){s+=x.s;return *this;} };
struct wxNativeFontInfo { PangoFontDescription* description=nullptr; std::string text; ~wxNativeFontInfo(){delete description;} std::string ToString()const{return text;} };
struct wxFont { std::shared_ptr<wxNativeFontInfo> info; std::string face; int size=0; wxFont():info(std::make_shared<wxNativeFontInfo>()){} const wxNativeFontInfo* GetNativeFontInfo()const{return info.get();} wxString GetFaceName()const{return wxString(face);} int GetPointSize()const{return size;} bool SetNativeFontInfo(const wxString& x){info->text=x.s; if(!info->description)info->description=new PangoFontDescription; info->description->text=x.s; face=x.s.substr(0,x.s.find(' ')); size=0; return true;} };
class wxFontButton;
template<class T> class wxWeakRef { public: wxWeakRef(T*); T* get()const{return token.expired()?nullptr:p;} private:T* p;std::weak_ptr<int> token; };
struct wxFontPickerEvent { wxFontPickerEvent(wxFontButton*,int,const wxFont&){} };
class wxFontButton { public: GtkWidget* m_widget; long m_windowStyle=0; wxFont m_selectedFont; std::shared_ptr<int> alive=std::make_shared<int>(1); int events=0; int id=7; bool destroy_on_set=false; wxFontButton(GtkWidget* w):m_widget(w){w->owner=this;if(w->child){w->child->owner=this;++w->child->refs;}} ~wxFontButton(); wxFont GetSelectedFont()const{return m_selectedFont;} int GetId()const{return id;} void SetNativeFontInfo(const char*); void UpdateFont(); void HandleWindowEvent(wxFontPickerEvent&){++events;} };
template<class T> wxWeakRef<T>::wxWeakRef(T* p):p(p),token(p->alive){}
static void mock_delete_control(wxFontButton* p) { delete p; }
static GtkWidget* mock_control_widget(wxFontButton* p) { return p->m_widget; }
static GtkRoot* gtk_widget_get_root(GtkWidget*) { return nullptr; }
const char kFontDialogPendingKey[] = "wx-font-dialog-pending";
// PRODUCTION_HELPERS
// PRODUCTION_DESTRUCTOR
// PRODUCTION_UPDATE
// PRODUCTION_SET_NATIVE

static void finish(bool success,const char* selected="Liberation Serif Bold Italic 10.5") { auto cb=pending_callback; auto data=pending_data; assert(cb&&data); pending_callback=nullptr;pending_data=nullptr;GAsyncResult r{success,selected};cb(G_OBJECT(gtk_font_dialog_new()),&r,data); }
static void finalize_widget(GtkWidget* w) { auto n=std::move(w->weak);w->weak.clear();w->alive=false;for(auto x:n)x.fn(x.data,G_OBJECT(w)); }
static void reset_async() { pending_callback=nullptr;pending_data=nullptr;pending_cancel=nullptr;open_count=0; }
int main() {
  // Full description label preserves style and fractional size; family-only style stays family-only.
  { GtkWidget w, label; w.child=&label; wxFontButton b(&w); b.m_selectedFont.SetNativeFontInfo(wxString("Noto Sans Bold Italic 9.5")); b.m_selectedFont.face="Noto Sans"; b.m_windowStyle=wxFNTP_FONTDESC_AS_LABEL; b.UpdateFont(); assert(label.label=="Noto Sans Bold Italic 9.5"); b.m_windowStyle=0; b.UpdateFont(); assert(label.label=="Noto Sans"); b.m_windowStyle=wxFNTP_USEFONT_FOR_LABEL; b.UpdateFont(); assert(label.attrs=="Noto Sans Bold Italic 9.5"); assert(b.events==0); }
  // Repeated activation opens only one dialog; success updates once and emits one event.
  { reset_async(); GtkWidget w,label;w.child=&label;wxFontButton b(&w);b.m_selectedFont.SetNativeFontInfo(wxString("Sans 10"));b.m_windowStyle=wxFNTP_FONTDESC_AS_LABEL;FontDialogButtonClicked(&w,&b);FontDialogButtonClicked(&w,&b);assert(open_count==1);finish(true);assert(b.events==1);assert(label.label=="Liberation Serif Bold Italic 10.5");assert(!g_object_get_data(G_OBJECT(&w),kFontDialogPendingKey)); }
  // Destroying the control cancels the async request; a late completion sees no live weak owner.
  { reset_async(); GtkWidget w,label;w.child=&label;auto* b=new wxFontButton(&w);b->m_selectedFont.SetNativeFontInfo(wxString("Sans 10"));FontDialogButtonClicked(&w,b);auto* c=pending_cancel;delete b;assert(c->cancelled);finalize_widget(&w);finish(true);assert(open_count==1); }
  // GTK label notification can destroy the owner during UpdateFont; completion must not reuse it.
  { reset_async(); GtkWidget w,label;w.child=&label;auto* b=new wxFontButton(&w);b->m_selectedFont.SetNativeFontInfo(wxString("Sans 10"));b->m_windowStyle=wxFNTP_FONTDESC_AS_LABEL;FontDialogButtonClicked(&w,b);destroy_on_label=true;finish(true);assert(label.label=="Liberation Serif Bold Italic 10.5");assert(!g_object_get_data(G_OBJECT(&w),kFontDialogPendingKey));finalize_widget(&w); }
  // A notify handler can detach the child label; UpdateFont keeps it alive through both setters.
  { GtkWidget w,label;w.child=&label;wxFontButton b(&w);b.m_selectedFont.SetNativeFontInfo(wxString("Serif 10.5"));b.m_windowStyle=wxFNTP_USEFONT_FOR_LABEL;detach_label_on_text=true;check_label_ref=true;b.UpdateFont();check_label_ref=false;assert(w.child==nullptr);assert(label.refs==1); }
  return 0;
}
