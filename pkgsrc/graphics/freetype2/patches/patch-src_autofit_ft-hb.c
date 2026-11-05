$NetBSD$

# EmberBSD: resolve optional HarfBuzz alongside the relocatable FreeType DSO.

--- src/autofit/ft-hb.c.orig
+++ src/autofit/ft-hb.c
@@ -36,7 +36,7 @@
 #    define FT_LIBHARFBUZZ "libharfbuzz-0.dll"
 #  else
 #    ifdef __APPLE__
-#      define FT_LIBHARFBUZZ "libharfbuzz.0.dylib"
+#      define FT_LIBHARFBUZZ "@loader_path/libharfbuzz.0.dylib"
 #    else
 #      define FT_LIBHARFBUZZ "libharfbuzz.so.0"
 #    endif
@@ -65,6 +65,45 @@
 #endif /* !_WIN32 */
 
 
+#ifdef __NetBSD__
+  /* dlopen uses the main executable's search path on NetBSD, not the
+   * calling DSO's.  First look next to this FreeType library so a relocated
+   * package prefix works without an environment variable. */
+  static const char  ft_hb_dso_anchor = 0;
+
+  static void *
+  ft_hb_load_sibling( FT_Memory  memory )
+  {
+    Dl_info      info;
+    const char*  slash;
+    char*        path = NULL;
+    void*        lib = NULL;
+    size_t       dirlen;
+    FT_Error     error;
+
+    if ( ft_strrchr( FT_LIBHARFBUZZ, '/' ) )
+      return NULL;
+    if ( !dladdr( &ft_hb_dso_anchor, &info ) || !info.dli_fname ||
+         info.dli_fname[0] != '/' )
+      return NULL;
+    slash = ft_strrchr( info.dli_fname, '/' );
+    if ( !slash )
+      return NULL;
+    dirlen = (size_t)( slash - info.dli_fname ) + 1;
+    if ( dirlen > FT_INT_MAX - sizeof ( FT_LIBHARFBUZZ ) )
+      return NULL;
+    if ( !FT_QALLOC( path, dirlen + sizeof ( FT_LIBHARFBUZZ ) ) )
+    {
+      ft_memcpy( path, info.dli_fname, dirlen );
+      ft_memcpy( path + dirlen, FT_LIBHARFBUZZ, sizeof ( FT_LIBHARFBUZZ ) );
+      lib = dlopen( path, RTLD_LAZY | RTLD_GLOBAL );
+      FT_FREE( path );
+    }
+    return lib;
+  }
+#endif
+
+
   FT_LOCAL_DEF( void )
   ft_hb_funcs_init( struct AF_ModuleRec_  *af_module )
   {
@@ -108,6 +147,22 @@
 #    define FT_RTLD_FLAGS RTLD_LAZY
 #  endif
 
+#  ifdef __NetBSD__
+    if ( !version_atleast )
+    {
+      lib = ft_hb_load_sibling( memory );
+      if ( lib )
+      {
+        version_atleast = DLSYM( lib, hb_version_atleast );
+        if ( !version_atleast )
+        {
+          dlclose( lib );
+          lib = NULL;
+        }
+      }
+    }
+#  endif
+
     if ( !version_atleast )
     {
       /* Load the HarfBuzz library.
