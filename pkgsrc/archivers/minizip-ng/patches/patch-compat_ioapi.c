# Restore zlib-compatible stdio callback defaults and retain Windows counterparts.
--- compat/ioapi.c.orig
+++ compat/ioapi.c
@@ -217,18 +217,197 @@
 
 /***************************************************************************/
 
-void fill_fopen_filefunc(zlib_filefunc_def *pzlib_filefunc_def) {
-    /* For 32-bit file support only, compile with MZ_FILE32_API */
-    if (pzlib_filefunc_def)
-        memset(pzlib_filefunc_def, 0, sizeof(zlib_filefunc_def));
+/* ioapi.h -- IO base function header for compress/uncompress .zip
+   part of the MiniZip project - ( https://www.winimage.com/zLibDll/minizip.html )
+
+         Copyright (C) 1998-2026 Gilles Vollant (minizip) ( https://www.winimage.com/zLibDll/minizip.html )
+
+         Modifications for Zip64 support
+         Copyright (C) 2009-2010 Mathias Svensson ( https://result42.com )
+
+         For more info read MiniZip_info.txt
+
+*/
+
+/* Stdio callbacks below are adapted from zlib 1.3.2 contrib/minizip/ioapi.c. */
+#include <limits.h>
+#include <stdio.h>
+#include <sys/types.h>
+#include <zlib.h>
+#if defined(_WIN32)
+typedef int64_t mz_stdio_offset_t;
+#define MZ_STDIO_TELL(stream) _ftelli64(stream)
+#define MZ_STDIO_SEEK(stream, offset, origin) _fseeki64(stream, offset, origin)
+#else
+typedef off_t mz_stdio_offset_t;
+#define MZ_STDIO_TELL(stream) ftello(stream)
+#define MZ_STDIO_SEEK(stream, offset, origin) fseeko(stream, offset, origin)
+#endif
+
+static voidpf ZCALLBACK fopen_file_func(voidpf opaque, const char* filename, int mode) {
+    FILE* file = NULL;
+    const char* mode_fopen = NULL;
+    (void)opaque;
+    if ((mode & ZLIB_FILEFUNC_MODE_READWRITEFILTER)==ZLIB_FILEFUNC_MODE_READ)
+        mode_fopen = "rb";
+    else
+    if (mode & ZLIB_FILEFUNC_MODE_EXISTING)
+        mode_fopen = "r+b";
+    else
+    if (mode & ZLIB_FILEFUNC_MODE_CREATE)
+        mode_fopen = "wb";
+
+    if ((filename!=NULL) && (mode_fopen != NULL))
+        file = fopen(filename, mode_fopen);
+    return file;
 }
 
-void fill_fopen64_filefunc(zlib_filefunc64_def *pzlib_filefunc_def) {
-    /* All mz_stream_os_* support large files if compilation supports it */
-    if (pzlib_filefunc_def)
-        memset(pzlib_filefunc_def, 0, sizeof(zlib_filefunc64_def));
+static voidpf ZCALLBACK fopen64_file_func(voidpf opaque, const void* filename, int mode) {
+    FILE* file = NULL;
+    const char* mode_fopen = NULL;
+    (void)opaque;
+    if ((mode & ZLIB_FILEFUNC_MODE_READWRITEFILTER)==ZLIB_FILEFUNC_MODE_READ)
+        mode_fopen = "rb";
+    else
+    if (mode & ZLIB_FILEFUNC_MODE_EXISTING)
+        mode_fopen = "r+b";
+    else
+    if (mode & ZLIB_FILEFUNC_MODE_CREATE)
+        mode_fopen = "wb";
+
+    if ((filename!=NULL) && (mode_fopen != NULL))
+        file = fopen((const char*)filename, mode_fopen);
+    return file;
+}
+
+
+static uLong ZCALLBACK fread_file_func(voidpf opaque, voidpf stream, void* buf, uLong size) {
+    uLong ret;
+    (void)opaque;
+    ret = (uLong)fread(buf, 1, (size_t)size, (FILE *)stream);
+    return ret;
+}
+
+static uLong ZCALLBACK fwrite_file_func(voidpf opaque, voidpf stream, const void* buf, uLong size) {
+    uLong ret;
+    (void)opaque;
+    ret = (uLong)fwrite(buf, 1, (size_t)size, (FILE *)stream);
+    return ret;
+}
+
+static long ZCALLBACK ftell_file_func(voidpf opaque, voidpf stream) {
+    long ret;
+    (void)opaque;
+    ret = ftell((FILE *)stream);
+    return ret;
+}
+
+
+static ZPOS64_T ZCALLBACK ftell64_file_func(voidpf opaque, voidpf stream) {
+    ZPOS64_T ret;
+    (void)opaque;
+    ret = (ZPOS64_T)MZ_STDIO_TELL((FILE *)stream);
+    return ret;
+}
+
+static long ZCALLBACK fseek_file_func(voidpf opaque, voidpf stream, uLong offset, int origin) {
+    int fseek_origin=0;
+    long ret;
+    (void)opaque;
+    switch (origin)
+    {
+    case ZLIB_FILEFUNC_SEEK_CUR :
+        fseek_origin = SEEK_CUR;
+        break;
+    case ZLIB_FILEFUNC_SEEK_END :
+        fseek_origin = SEEK_END;
+        break;
+    case ZLIB_FILEFUNC_SEEK_SET :
+        fseek_origin = SEEK_SET;
+        break;
+    default: return -1;
+    }
+    ret = 0;
+    if (origin == ZLIB_FILEFUNC_SEEK_SET && offset > LONG_MAX)
+        return -1;
+    long signed_offset = offset <= LONG_MAX ? (long)offset :
+        -1L - (long)(ULONG_MAX - offset);
+    if (fseek((FILE *)stream, signed_offset, fseek_origin) != 0)
+        ret = -1;
+    return ret;
+}
+
+static long ZCALLBACK fseek64_file_func(voidpf opaque, voidpf stream, ZPOS64_T offset, int origin) {
+    int fseek_origin=0;
+    long ret;
+    (void)opaque;
+    switch (origin)
+    {
+    case ZLIB_FILEFUNC_SEEK_CUR :
+        fseek_origin = SEEK_CUR;
+        break;
+    case ZLIB_FILEFUNC_SEEK_END :
+        fseek_origin = SEEK_END;
+        break;
+    case ZLIB_FILEFUNC_SEEK_SET :
+        fseek_origin = SEEK_SET;
+        break;
+    default: return -1;
+    }
+    ret = 0;
+
+    if (origin == ZLIB_FILEFUNC_SEEK_SET && offset > INT64_MAX)
+        return -1;
+    int64_t signed_offset = offset <= INT64_MAX ? (int64_t)offset :
+        -1 - (int64_t)(UINT64_MAX - offset);
+    mz_stdio_offset_t converted_offset = (mz_stdio_offset_t)signed_offset;
+    if ((int64_t)converted_offset != signed_offset ||
+        MZ_STDIO_SEEK((FILE *)stream, converted_offset, fseek_origin) != 0)
+        ret = -1;
+
+    return ret;
+}
+
+
+static int ZCALLBACK fclose_file_func(voidpf opaque, voidpf stream) {
+    int ret;
+    (void)opaque;
+    ret = fclose((FILE *)stream);
+    return ret;
+}
+
+static int ZCALLBACK ferror_file_func(voidpf opaque, voidpf stream) {
+    int ret;
+    (void)opaque;
+    ret = ferror((FILE *)stream);
+    return ret;
+}
+
+void fill_fopen_filefunc(zlib_filefunc_def* pzlib_filefunc_def) {
+    if (!pzlib_filefunc_def) return;
+    pzlib_filefunc_def->zopen_file = fopen_file_func;
+    pzlib_filefunc_def->zread_file = fread_file_func;
+    pzlib_filefunc_def->zwrite_file = fwrite_file_func;
+    pzlib_filefunc_def->ztell_file = ftell_file_func;
+    pzlib_filefunc_def->zseek_file = fseek_file_func;
+    pzlib_filefunc_def->zclose_file = fclose_file_func;
+    pzlib_filefunc_def->zerror_file = ferror_file_func;
+    pzlib_filefunc_def->opaque = NULL;
+}
+
+void fill_fopen64_filefunc(zlib_filefunc64_def* pzlib_filefunc_def) {
+    if (!pzlib_filefunc_def) return;
+    pzlib_filefunc_def->zopen64_file = fopen64_file_func;
+    pzlib_filefunc_def->zread_file = fread_file_func;
+    pzlib_filefunc_def->zwrite_file = fwrite_file_func;
+    pzlib_filefunc_def->ztell64_file = ftell64_file_func;
+    pzlib_filefunc_def->zseek64_file = fseek64_file_func;
+    pzlib_filefunc_def->zclose_file = fclose_file_func;
+    pzlib_filefunc_def->zerror_file = ferror_file_func;
+    pzlib_filefunc_def->opaque = NULL;
 }
 
+#if !defined(_WIN32)
 void fill_win32_filefunc(zlib_filefunc_def *pzlib_filefunc_def) {
     /* Handled by mz_stream_os_win32 */
     if (pzlib_filefunc_def)
@@ -251,6 +430,8 @@
    support is automatically handled by the underlying os stream. Do not
    pass wide-characters to zipOpen or unzOpen. */
 
+#endif  /* !defined(_WIN32) */
+
 void fill_memory_filefunc(zlib_filefunc_def *pzlib_filefunc_def) {
     /* Use opaque to indicate which stream interface to create */
     if (pzlib_filefunc_def) {
