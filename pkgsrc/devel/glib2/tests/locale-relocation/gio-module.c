#include <gio/gio.h>
#include <stdio.h>
#include <stdlib.h>
__attribute__((constructor)) static void mark(void) { const char *p=getenv("EMBER_GIO_MODULE_MARKER"); if(p){FILE *f=fopen(p,"w");if(f){fputs("loaded",f);fclose(f);}} }
void g_io_module_load(GIOModule *m) {(void)m;}
void g_io_module_unload(GIOModule *m) {(void)m;}
