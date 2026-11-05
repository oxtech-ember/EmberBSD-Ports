#include <gio/gio.h>
#include <stdio.h>
#include <string.h>
static const char *one, *two;
static gint failed;
static char *guess(void) { gboolean u; return g_content_type_guess("probe.emberunique123", NULL, 0, &u); }
static void set(const char *p) { const char *dirs[] = {p, NULL}; g_content_type_set_mime_dirs(dirs); }
static gpointer query(gpointer ignored) {
 (void)ignored;
 for(int i=0;i<150;i++) { char *s=guess(); if(strcmp(s,"application/x-ember-alpha") && strcmp(s,"application/x-ember-beta")) g_atomic_int_set(&failed,1); g_free(s); if(i%15==0) { GList *types=g_content_types_get_registered(); g_list_free_full(types,g_free); } }
 return NULL;
}
static gpointer change(gpointer ignored) {(void)ignored;for(int i=0;i<150;i++)set((i&1)?one:two);return NULL;}
static int match(const char *expected) {char *s=guess();int ok=!strcmp(s,expected); if(!ok)fprintf(stderr,"wanted %s got %s\n",expected,s);g_free(s);return ok;}
int main(int n,char **v) {
 if(n!=4)return 2;one=v[2];two=v[3];
 if(!strcmp(v[1],"before")){set(one);return !match("application/x-ember-alpha");}
 if(!strcmp(v[1],"after")){if(!match("application/x-ember-relocated-unique"))return 1;set(two);return !match("application/x-ember-beta");}
 if(!strcmp(v[1],"threads")){GThread *t[4];set(one);for(int i=0;i<3;i++)t[i]=g_thread_new("query",query,NULL);t[3]=g_thread_new("setter",change,NULL);for(int i=0;i<4;i++)g_thread_join(t[i]);return g_atomic_int_get(&failed);}
 return 2;
}
