$NetBSD$

Probe the selected POSIX C++ command without an implicit system shell.
Use the recorded GN commit position when a source archive has no .git directory.
Preserve an explicit Darwin SDK deployment target instead of appending version 14.

The archive-version approach follows FreeBSD devel/gn/files/patch-build_gen.py
(by Oleh Hushchenkov and the FreeBSD Ports contributors). Retain the original
Chromium copyright and BSD-style license. This variant preserves the upstream
header format and validates the complete position/hash string.
Origin: EmberBSD (AI-assisted), not submitted upstream.

--- build/gen.py.orig
+++ build/gen.py
@@ -237,8 +237,9 @@
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
@@ -247,7 +248,14 @@
 
 def GenerateLastCommitPosition(host, header):
   ROOT_TAG = 'initial-commit'
-  if os.path.isdir(os.path.join(REPO_ROOT, '.git')):
+  version = os.environ.get('GN_VERSION')
+  if version is not None:
+    # Source archives have no .git directory. Keep the pinned commit identity.
+    mo = re.fullmatch(r'([0-9]+) \(([0-9a-f]{12})\)', version)
+    if not mo:
+      raise ValueError('GN_VERSION must be a commit position and short hash')
+    num, commit_id = mo.groups()
+  elif os.path.isdir(os.path.join(REPO_ROOT, '.git')):
     describe_output = subprocess.check_output(
         ['git', 'describe', 'HEAD', '--abbrev=12', '--match', ROOT_TAG],
         shell=host.is_windows(), cwd=REPO_ROOT)
@@ -562,8 +570,12 @@
       # Feel free to bump this value whenever you want, as long as all non-EOL
       # macOS versions are supported.
       min_mac_version_flag = '-mmacosx-version-min=14'
-      cflags.append(min_mac_version_flag)
-      ldflags.append(min_mac_version_flag)
+      # Keep an explicit SDK deployment target. Use the upstream default only
+      # when no minimum version was supplied for that command.
+      if not any(flag.startswith('-mmacosx-version-min=') for flag in cflags):
+        cflags.append(min_mac_version_flag)
+      if not any(flag.startswith('-mmacosx-version-min=') for flag in ldflags):
+        ldflags.append(min_mac_version_flag)
     elif platform.is_aix():
       cflags.append('-maix64')
       ldflags.append('-maix64')
