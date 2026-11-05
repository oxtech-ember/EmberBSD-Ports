#include <glib.h>
#include <gio/gio.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
typedef gchar *(*resolver)(const void *, const char *, const char *);
int main(int argc, char **argv) {
 if(argc < 2) return 2;
 if(!strcmp(argv[1],"resolve")) {
  if(argc!=5)return 2;
  const void *anchor = strcmp(argv[2],"static") ? dlsym(RTLD_DEFAULT,"_glib_relocate_owned_path") : (void *)&main;
  resolver fn=(resolver)dlsym(RTLD_DEFAULT,"_glib_relocate_owned_path"); if(!fn)return 5; gchar *p=fn(anchor,argv[3],argv[4]); puts(p); g_free(p); return 0;
 }
 if(!strcmp(argv[1],"mime-init")) { g_content_type_get_mime_dirs(); argv[1]="mime"; }
 if(!strcmp(argv[1],"mime")) { gboolean uncertain=FALSE; gchar *v=g_content_type_guess("probe.emberunique123",NULL,0,&uncertain);puts(v);g_free(v);return 0; }
 if(!strcmp(argv[1],"modules")) { g_vfs_get_default(); return 0; }
 if(!strcmp(argv[1],"loaded")) { Dl_info i; if(!dladdr((void*)g_get_system_data_dirs,&i))return 6; puts(i.dli_fname); return 0; }
 if(!strcmp(argv[1],"xdg")) {
  const gchar * const *d=g_get_system_data_dirs(), * const *c=g_get_system_config_dirs();
  for(;*d;d++)printf("data=%s\n",*d);for(;*c;c++)printf("config=%s\n",*c);return 0;
 }
 if(!strcmp(argv[1],"alias")) {const gchar * const *p=g_get_language_names();for(;*p;p++)puts(*p);return 0;}
 if(!strcmp(argv[1],"launch")) {
  GError *err=NULL;GDesktopAppInfo *app=g_desktop_app_info_new_from_filename(argv[2]); if(!app)return 3;
  gboolean ok=g_app_info_launch(G_APP_INFO(app),NULL,NULL,&err); if(!ok) fprintf(stderr,"%s\n",err->message);g_object_unref(app);return ok?0:4;
 }
 return 2;
}
