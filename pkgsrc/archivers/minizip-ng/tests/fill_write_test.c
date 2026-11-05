#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "ioapi.h"
#include "zip.h"
#include "unzip.h"
static void *open_cb(void*o,const void *path,int mode){(void)o;const char*m=(mode&ZLIB_FILEFUNC_MODE_READWRITEFILTER)==ZLIB_FILEFUNC_MODE_READ?"rb":(mode&ZLIB_FILEFUNC_MODE_CREATE)?"wb":"r+b";return fopen(path,m);}
static int close_cb(void*o,void*stream){(void)o;return fclose(stream);}
int main(int argc,char**argv){if(argc!=2)return 2;zlib_filefunc64_def f;fill_fopen64_filefunc(&f);if(!f.zread_file||!f.zwrite_file||!f.ztell64_file||!f.zseek64_file||!f.zerror_file)return 3;f.zopen64_file=open_cb;f.zclose_file=close_cb;zipFile z=zipOpen2_64(argv[1],APPEND_STATUS_CREATE,0,&f);if(!z)return 4;if(zipOpenNewFileInZip64(z,"a",0,0,0,0,0,0,0,0,0)!=ZIP_OK)return 5;if(zipWriteInFileInZip(z,"abc",3)!=ZIP_OK)return 6;if(zipCloseFileInZip(z)!=ZIP_OK||zipClose(z,0)!=ZIP_OK)return 7;unzFile u=unzOpen2_64(argv[1],&f);if(!u||unzGoToFirstFile(u)!=UNZ_OK||unzOpenCurrentFile(u)!=UNZ_OK)return 8;char b[3];int n=unzReadCurrentFile(u,b,3);if(n!=3||memcmp(b,"abc",3))return 9;if(unzCloseCurrentFile(u)!=UNZ_OK||unzClose(u)!=UNZ_OK)return 10;return 0;}
