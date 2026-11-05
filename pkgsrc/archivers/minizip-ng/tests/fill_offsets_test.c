#include <stdint.h>
#include <stdio.h>
#include "ioapi.h"
int main(int argc,char **argv){if(argc!=2)return 2;zlib_filefunc64_def f;fill_fopen64_filefunc(&f);void*s=f.zopen64_file(0,argv[1],ZLIB_FILEFUNC_MODE_CREATE);if(!s)return 3;uint64_t n=UINT64_C(4294967313);if(f.zseek64_file(0,s,n,ZLIB_FILEFUNC_SEEK_SET)||f.ztell64_file(0,s)!=n)return 4;if(f.zwrite_file(0,s,"x",1)!=1)return 5;if(f.zseek64_file(0,s,UINT64_MAX,ZLIB_FILEFUNC_SEEK_SET)!=-1)return 6;if(f.zseek64_file(0,s,UINT64_MAX,ZLIB_FILEFUNC_SEEK_CUR)||f.ztell64_file(0,s)!=n)return 7;if(f.zclose_file(0,s))return 8;zlib_filefunc_def q;fill_fopen_filefunc(&q);if(!q.zopen_file||!q.zread_file||!q.zwrite_file||!q.ztell_file||!q.zseek_file||!q.zclose_file||!q.zerror_file)return 9;return 0;}
