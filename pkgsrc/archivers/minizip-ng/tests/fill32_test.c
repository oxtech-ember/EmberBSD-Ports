#include <stdio.h>
#include <limits.h>
#include <string.h>
#include "ioapi.h"
#include "unzip.h"
static void *open_cb(void*o,const char *path,int mode){(void)o;(void)mode;return fopen(path,"rb");}
static int close_cb(void*o,void*stream){(void)o;return fclose(stream);}
int main(int argc,char**argv){if(argc!=2)return 2;zlib_filefunc_def f;fill_fopen_filefunc(&f);void*s=f.zopen_file(0,argv[1],ZLIB_FILEFUNC_MODE_READ);if(!s)return 3;if(f.zseek_file(0,s,5,ZLIB_FILEFUNC_SEEK_SET)||f.ztell_file(0,s)!=5)return 4;if(f.zseek_file(0,s,ULONG_MAX,ZLIB_FILEFUNC_SEEK_CUR)||f.ztell_file(0,s)!=4)return 5;if(f.zseek_file(0,s,ULONG_MAX,ZLIB_FILEFUNC_SEEK_SET)!=-1)return 6;if(f.zclose_file(0,s))return 7;f.zopen_file=open_cb;f.zclose_file=close_cb;unzFile z=unzOpen2(argv[1],&f);if(!z)return 8;int v=unzGoToFirstFile(z);unzClose(z);return v!=UNZ_OK;}
