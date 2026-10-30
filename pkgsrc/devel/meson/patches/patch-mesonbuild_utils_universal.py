$NetBSD$

Use the selected native lipo for Darwin architecture checks.

--- mesonbuild/utils/universal.py.orig
+++ mesonbuild/utils/universal.py
@@ -811,13 +811,13 @@
     return platform.system().lower() == 'os/2'
 
 @lru_cache(maxsize=None)
-def darwin_get_object_archs(objpath: str) -> 'ImmutableListProtocol[str]':
+def darwin_get_object_archs(objpath: str, lipo: T.Tuple[str, ...] = ('lipo',)) -> 'ImmutableListProtocol[str]':
     '''
     For a specific object (executable, static library, dylib, etc), run `lipo`
     to fetch the list of archs supported by it. Supports both thin objects and
     'fat' objects.
     '''
-    _, stdo, stderr = Popen_safe(['lipo', '-info', objpath])
+    _, stdo, stderr = Popen_safe([*lipo, '-info', objpath])
     if not stdo:
         mlog.debug(f'lipo {objpath}: {stderr}')
         return None
