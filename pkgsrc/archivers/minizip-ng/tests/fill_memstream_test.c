#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ioapi.h"
#include "zip.h"
typedef struct {char *buffer; size_t size;} state;
static void *open_cb(void*opaque,const char*name,int mode){(void)name;(void)mode;state*s=opaque;return open_memstream(&s->buffer,&s->size);}
static int close_cb(void*opaque,void*stream){(void)opaque;return fclose(stream);}
int main(int argc,char**argv){if(argc!=2)return 2;state s={0};zlib_filefunc_def f;fill_fopen_filefunc(&f);f.opaque=&s;f.zopen_file=open_cb;f.zclose_file=close_cb;zipFile z=zipOpen2(NULL,APPEND_STATUS_CREATE,NULL,&f);if(!z)return 3;if(zipOpenNewFileInZip(z,"a",NULL,NULL,0,NULL,0,NULL,0,0)!=ZIP_OK)return 4;if(zipWriteInFileInZip(z,"abc",3)!=ZIP_OK)return 5;if(zipCloseFileInZip(z)!=ZIP_OK||zipClose(z,NULL)!=ZIP_OK)return 6;FILE*out=fopen(argv[1],"wb");if(!out||fwrite(s.buffer,1,s.size,out)!=s.size||fclose(out))return 7;free(s.buffer);return 0;}
