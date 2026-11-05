#include <tiffio.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
static char diagnostic[256];
static int handler(TIFF *tif, void *ctx, const char *module, const char *fmt, va_list args) {
    (void)tif;(void)ctx;(void)module;vsnprintf(diagnostic,sizeof(diagnostic),fmt,args);return 1;
}
int main(int argc, char **argv) {
    if(argc!=3)return 11;
    TIFFOpenOptions *opt=TIFFOpenOptionsAlloc(); if(!opt)return 10;
    TIFFOpenOptionsSetMaxSingleMemAlloc(opt,1048576); TIFFOpenOptionsSetMaxCumulatedMemAlloc(opt,1048576);
    TIFFOpenOptionsSetErrorHandlerExtR(opt,handler,NULL);
    TIFFOpenOptionsSetWarningHandlerExtR(opt,handler,NULL);
    TIFF *tif=TIFFOpenExt(argv[1],"r",opt);TIFFOpenOptionsFree(opt);
    if(!strcmp(argv[2],"normal")) {if(!tif){puts(diagnostic);return 12;} TIFFClose(tif); puts("ordinary strip PASS");return 0;}
    if(tif){TIFFClose(tif);return 13;} puts(diagnostic);
    return strstr(diagnostic,"Cannot handle 2147483648 number of strips") ? 0 : 14;
}
