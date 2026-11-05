#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "ioapi.h"
#include "unzip.h"
typedef struct { unsigned char *p; size_t size, pos; } memory;
static void *open_cb(void *opaque,const void *name,int mode){(void)name;(void)mode;memory*m=opaque;m->pos=0;return m;}
static unsigned long read_cb(void *opaque,void *stream,void *buf,unsigned long len){(void)opaque;memory*m=stream;size_t n=m->size-m->pos;if(n>len)n=len;memcpy(buf,m->p+m->pos,n);m->pos+=n;return n;}
static unsigned long write_cb(void*o,void*s,const void*b,unsigned long n){(void)o;(void)s;(void)b;(void)n;return 0;}
static ZPOS64_T tell_cb(void*o,void*s){(void)o;return ((memory*)s)->pos;}
static long seek_cb(void*o,void*s,ZPOS64_T offset,int origin){(void)o;memory*m=s;int64_t base=origin==ZLIB_FILEFUNC_SEEK_SET?0:origin==ZLIB_FILEFUNC_SEEK_CUR?(int64_t)m->pos:(int64_t)m->size;int64_t pos=base+(int64_t)offset;if(pos<0||(uint64_t)pos>m->size)return -1;m->pos=pos;return 0;}
static int close_cb(void*o,void*s){(void)o;(void)s;return 0;}
static int error_cb(void*o,void*s){(void)o;(void)s;return 0;}
int main(int argc,char**argv){if(argc!=3)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 3;fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);memory m={malloc((size_t)n),(size_t)n,0};if(!m.p||fread(m.p,1,m.size,f)!=m.size)return 4;fclose(f);
 zlib_filefunc64_def cb={open_cb,read_cb,write_cb,tell_cb,seek_cb,close_cb,error_cb,&m};unzFile z=unzOpen2_64(NULL,&cb);if(!z){puts("open failed");return 5;}if(unzGoToFirstFile(z)!=UNZ_OK)return 6;int method=0,level=0;if(unzOpenCurrentFile2(z,&method,&level,1)!=UNZ_OK)return 7;uint64_t actual=unzGetCurrentFileZStreamPos64(z),expected=strtoull(argv[2],NULL,10);printf("method=%d expected=%llu actual=%llu\n",method,(unsigned long long)expected,(unsigned long long)actual);int ok=actual==expected;if(unzCloseCurrentFile(z)!=UNZ_OK)ok=0;
 if(unzOpenCurrentFile(z)!=UNZ_OK)ok=0;
 unsigned char output[512]; int count=unzReadCurrentFile(z,output,sizeof(output));
 const char *pattern="test model metadata content"; size_t width=strlen(pattern);
 if(count!=(int)(8*width))ok=0;
 for(int i=0;i<8 && count==(int)(8*width);i++)if(memcmp(output+i*width,pattern,width))ok=0;
 if(unzCloseCurrentFile(z)!=UNZ_OK)ok=0;if(unzClose(z)!=UNZ_OK)ok=0;free(m.p);return ok?0:8;}
