#include <stdio.h>
#include "ioapi.h"
#include "unzip.h"
static void *open_cb(void*o,const void *path,int mode){(void)o;(void)mode;return fopen(path,"rb");}
static int close_cb(void*o,void*stream){(void)o;return fclose(stream);}
int main(int argc,char**argv){if(argc!=2)return 2;zlib_filefunc64_def f;fill_fopen64_filefunc(&f);f.zopen64_file=open_cb;f.zclose_file=close_cb;unzFile z=unzOpen2_64(argv[1],&f);if(!z){puts("partial callbacks: open failed");return 3;}int status=unzGoToFirstFile(z);unzClose(z);printf("partial callbacks status %d\n",status);return status!=UNZ_OK;}
