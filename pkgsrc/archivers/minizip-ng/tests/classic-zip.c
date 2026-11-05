/* SPDX-License-Identifier: BSD-2-Clause */
/* Synthetic MZ_COMPAT regression: byte-safe UTF-8 and legacy case flags. */
#include <minizip-ng/zip.h>
#include <minizip-ng/unzip.h>
#include <stdio.h>
#include <string.h>
int main(void) {
 const char *name="MiXeD-\xd1\x82\xd0\xb5\xd1\x81\xd1\x82.txt";
 const char *lower="mixed-\xd1\x82\xd0\xb5\xd1\x81\xd1\x82.txt", text[]="synthetic payload";
 char buf[64]={0}; zipFile z=zipOpen64("classic.zip",APPEND_STATUS_CREATE); if(!z)return 1;
 if(zipOpenNewFileInZip(z,name,NULL,NULL,0,NULL,0,NULL,Z_DEFLATED,Z_DEFAULT_COMPRESSION)!=ZIP_OK||zipWriteInFileInZip(z,text,sizeof(text)-1)!=ZIP_OK||zipCloseFileInZip(z)!=ZIP_OK)return 2;
 if(zipOpenNewFileInZip(z,"empty.txt",NULL,NULL,0,NULL,0,NULL,Z_DEFLATED,Z_DEFAULT_COMPRESSION)!=ZIP_OK||zipCloseFileInZip(z)!=ZIP_OK||zipClose(z,NULL)!=ZIP_OK)return 3;
 unzFile u=unzOpen64("classic.zip");if(!u)return 4;
 if(unzLocateFile(u,name,0)!=UNZ_OK || unzLocateFile(u,name,1)!=UNZ_OK || unzLocateFile(u,name,2)!=UNZ_OK)return 5;
#ifdef _WIN32
 if(unzLocateFile(u,lower,0)!=UNZ_OK)return 6;
#else
 if(unzLocateFile(u,lower,0)==UNZ_OK)return 6;
#endif
 if(unzLocateFile(u,lower,1)==UNZ_OK||unzLocateFile(u,lower,2)!=UNZ_OK)return 7;
 if(unzLocateFile(u,name,1)!=UNZ_OK||unzOpenCurrentFile(u)!=UNZ_OK)return 8;
 int n=unzReadCurrentFile(u,buf,sizeof buf);if(n!=(int)sizeof(text)-1||memcmp(buf,text,sizeof(text)-1)||unzCloseCurrentFile(u)!=UNZ_OK)return 9;
 if(unzLocateFile(u,"empty.txt",1)!=UNZ_OK||unzOpenCurrentFile(u)!=UNZ_OK||unzReadCurrentFile(u,buf,sizeof buf)!=0||unzCloseCurrentFile(u)!=UNZ_OK||unzClose(u)!=UNZ_OK)return 10;
 FILE *f=fopen("invalid.zip","wb");if(!f)return 11;fwrite("PK\003",1,3,f);fclose(f);u=unzOpen64("invalid.zip");if(u){unzClose(u);return 12;}
 remove("classic.zip");remove("invalid.zip");puts("MZ_COMPAT UTF-8, case flags, empty entry, invalid archive: PASS");return 0;
}
