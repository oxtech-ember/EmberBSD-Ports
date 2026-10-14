$NetBSD$

Describe the NetBSD target loader, platform, version and ABI during a cross
build. Do not derive target facts from a different host Python 3.14 build.
The caller declares the runtime platform; source headers supply the version.
Use the installed configuration directory for the POSIX static library.

Origin: EmberBSD (AI-assisted), macOS-to-NetBSD package metadata.
Not submitted or accepted upstream.

--- Tools/build/generate-build-details.py.orig
+++ Tools/build/generate-build-details.py
@@ -63,11 +63,42 @@
 
     data['abi']['flags'] = list(sys.abiflags)
 
+    extension_suffixes = importlib.machinery.EXTENSION_SUFFIXES
+    if ('_PYTHON_HOST_PLATFORM' in os.environ
+            and sysconfig.get_platform().startswith('netbsd')):
+        # The build interpreter may have a different micro version or ABI.
+        data['platform'] = os.environ['PYTHON_BUILD_DETAILS_PLATFORM']
+        header = os.path.join(os.path.dirname(__file__), '../../Include/patchlevel.h')
+        with open(header, encoding='utf-8') as stream:
+            constants = dict((parts[1], parts[2]) for line in stream
+                             if len(parts := line.split()) >= 3
+                             and parts[0] == '#define')
+        levels = {'PY_RELEASE_LEVEL_ALPHA': ('alpha', 0xA),
+                  'PY_RELEASE_LEVEL_BETA': ('beta', 0xB),
+                  'PY_RELEASE_LEVEL_GAMMA': ('candidate', 0xC),
+                  'PY_RELEASE_LEVEL_FINAL': ('final', 0xF)}
+        level, level_code = levels[constants['PY_RELEASE_LEVEL']]
+        version = {name: int(constants[f'PY_{name.upper()}_VERSION'])
+                   for name in ('major', 'minor', 'micro')}
+        version.update(releaselevel=level, serial=int(constants['PY_RELEASE_SERIAL']))
+        data['language']['version_info'] = version
+        data['implementation']['version'] = version
+        data['implementation']['hexversion'] = (
+            version['major'] << 24 | version['minor'] << 16 |
+            version['micro'] << 8 | level_code << 4 | version['serial'])
+        data['abi']['flags'] = list(sysconfig.get_config_var('ABIFLAGS'))
+        # Match the target's Python/dynload_shlib.c, not the build interpreter.
+        extension_suffixes = [f".{sysconfig.get_config_var('SOABI')}.so"]
+        alt_soabi = sysconfig.get_config_var('ALT_SOABI')
+        if alt_soabi:
+            extension_suffixes.append(f'.{alt_soabi}.so')
+        extension_suffixes.extend(['.abi3.so', '.so'])
+
     data['suffixes']['source'] = importlib.machinery.SOURCE_SUFFIXES
     data['suffixes']['bytecode'] = importlib.machinery.BYTECODE_SUFFIXES
     #data['suffixes']['optimized_bytecode'] = importlib.machinery.OPTIMIZED_BYTECODE_SUFFIXES
     #data['suffixes']['debug_bytecode'] = importlib.machinery.DEBUG_BYTECODE_SUFFIXES
-    data['suffixes']['extensions'] = importlib.machinery.EXTENSION_SUFFIXES
+    data['suffixes']['extensions'] = extension_suffixes
 
     LIBDIR = sysconfig.get_config_var('LIBDIR')
     LDLIBRARY = sysconfig.get_config_var('LDLIBRARY')
@@ -105,7 +136,7 @@
 
         # EXTENSION_SUFFIXES has been constant for a long time, and currently we
         # don't have a better information source to find the stable ABI suffix.
-        for suffix in importlib.machinery.EXTENSION_SUFFIXES:
+        for suffix in extension_suffixes:
             if suffix.startswith('.abi'):
                 data['abi']['stable_abi_suffix'] = suffix
                 break
@@ -121,7 +152,8 @@
         data['libpython']['link_extensions'] = bool(LIBPYTHON)
 
     if has_static_library:
-        data['libpython']['static'] = os.path.join(LIBDIR, LIBRARY)
+        static_dir = sysconfig.get_config_var('LIBPL') if os.name == 'posix' else LIBDIR
+        data['libpython']['static'] = os.path.join(static_dir, LIBRARY)
 
     data['c_api']['headers'] = INCLUDEPY
     if LIBPC:
