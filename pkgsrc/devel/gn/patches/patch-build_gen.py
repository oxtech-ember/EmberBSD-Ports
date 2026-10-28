$NetBSD$

Use explicit selected tools, a pinned version and shared CXX headers.
Origin: EmberBSD (AI-assisted).

--- build/gen.py.orig
+++ build/gen.py
@@ -15,8 +15,7 @@
 import sys
 
 from ninja_file import NinjaFile, escape_path_ninja
-from pinned import get_toolchain, install
-from target import Arch, Platform, Target
+from target import Platform
 
 assert sys.version_info >= (3, 9, 0)
 
@@ -169,8 +168,9 @@
 def is_gcc(cxx):
   """Return True iff the compiler at `cxx` is GCC based."""
   ret = subprocess.run(
-      f'{cxx} -dM -E -',
-      shell=True,
+      (shlex.split(cxx) + ['-dM', '-E', '-']
+       if os.name != 'nt' else f'{cxx} -dM -E -'),
+      shell=os.name == 'nt',
       stdin=subprocess.DEVNULL,
       text=True,
       capture_output=True)
@@ -179,7 +179,14 @@
 
 def GenerateLastCommitPosition(host, header, generate_dummy):
   ROOT_TAG = 'initial-commit'
-  if not generate_dummy and os.path.isdir(os.path.join(REPO_ROOT, '.git')):
+  version = os.environ.get('GN_VERSION')
+  if not generate_dummy and version is not None:
+    # Source archives have no .git directory. Keep the selected commit identity.
+    mo = re.fullmatch(r'([0-9]+) \(([0-9a-f]{12})\)', version)
+    if not mo:
+      raise ValueError('GN_VERSION must be a commit position and short hash')
+    num, commit_id = mo.groups()
+  elif not generate_dummy and os.path.isdir(os.path.join(REPO_ROOT, '.git')):
     describe_output = subprocess.check_output(
         ['git', 'describe', 'HEAD', '--abbrev=12', '--match', ROOT_TAG],
         shell=host.is_windows(), cwd=REPO_ROOT)
@@ -359,11 +366,12 @@
     }
     ninja.CargoLibTarget(
         library_to_a('gn_starlark'),
+        cargo_flags='--offline --locked',
         **starlark_common_args,
     )
     rust_tests = ninja.CargoTestTarget(
         'rust_unittests',
-        cargo_flags='--workspace',
+        cargo_flags='--workspace --offline --locked',
         implicit_inputs=[
             library_to_a('base'),
             library_to_a('gn_lib'),
@@ -446,6 +454,8 @@
           ['ninja', '-C', build_dir, '-t', 'compdb'], stdout=f, check=True)
 
 def WriteGNNinja(path, platform, host, options, args_list):
+  if not os.environ.get('CXX') or not os.environ.get('AR'):
+    raise ValueError('select explicit CXX and AR from the build toolchain')
   cflags = []
   ldflags = []
   if platform.is_msvc():
@@ -460,30 +470,21 @@
     cxx = os.environ.get('CXX', 'g++')
     ld = os.environ.get('LD', 'g++')
     ar = os.environ.get('AR', 'ar')
-  # Linux and mac are currently the only supported hosts for hermetic clang.
-  elif not (cxx := os.environ.get('CXX')) and any([platform.is_linux(), platform.is_darwin()]):
-    target = Target(platform, Arch.target())
-    toolchain = get_toolchain(Target.host(), target)
-    install(toolchain.packages)
-
-    cxx = toolchain.env['CXX']
-    ld = os.environ.get('LD', toolchain.env['LD'])
-    ar = os.environ.get('AR', toolchain.env['AR'])
-    if toolchain.sysroot:
-      cflags.append(f'--sysroot={toolchain.sysroot}')
-      ldflags.append(f'--sysroot={toolchain.sysroot}')
   else:
-    cxx = cxx or 'clang++'
+    cxx = os.environ['CXX']
     ld = os.environ.get('LD', cxx)
-    ar = os.environ.get('AR', 'ar')
+    ar = os.environ['AR']
 
   cflags += os.environ.get('CFLAGS', '').split()
   cflags += os.environ.get('CXXFLAGS', '').split()
   ldflags += os.environ.get('LDFLAGS', '').split()
   libflags = os.environ.get('LIBFLAGS', '').split()
+  cxx_include = os.environ.get('GN_CXX_INCLUDE', '')
+  if not os.path.isabs(cxx_include) or not os.path.isfile(os.path.join(cxx_include, 'rust/cxx.h')):
+    raise RuntimeError('GN_CXX_INCLUDE must name the selected CXX include directory')
   include_dirs = [
       os.path.relpath(os.path.join(REPO_ROOT, 'src'), os.path.dirname(path)),
-      os.path.relpath(os.path.join(REPO_ROOT, 'src/gn/starlark/vendor/cxx/include'), os.path.dirname(path)),
+      cxx_include,
       '.',
   ]
   if platform.is_zos():
@@ -598,8 +599,11 @@
       # Feel free to bump this value whenever you want, as long as all non-EOL
       # macOS versions are supported.
       min_mac_version_flag = '-mmacosx-version-min=14'
-      cflags.append(min_mac_version_flag)
-      ldflags.append(min_mac_version_flag)
+      # Keep explicit SDK deployment targets for each command.
+      if not any(flag.startswith('-mmacosx-version-min=') for flag in cflags):
+        cflags.append(min_mac_version_flag)
+      if not any(flag.startswith('-mmacosx-version-min=') for flag in ldflags):
+        ldflags.append(min_mac_version_flag)
     elif platform.is_aix():
       cflags.append('-maix64')
       ldflags.append('-maix64')
