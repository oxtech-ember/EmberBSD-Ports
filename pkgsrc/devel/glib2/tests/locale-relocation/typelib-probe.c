#include <girepository/girepository.h>
#include <stdio.h>
int main(void) {
 GError *e=NULL; GIRepository *r=gi_repository_new();size_t n;const char *const *p=gi_repository_get_search_path(r,&n);
 for(size_t i=0;i<n;i++)printf("search=%s\n",p[i]);
 if(!gi_repository_require(r,"GLib","2.0",0,&e)){fprintf(stderr,"%s\n",e->message);return 1;}
 printf("loaded=%s\n",gi_repository_get_typelib_path(r,"GLib"));g_object_unref(r);return 0;
}
