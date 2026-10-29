$NetBSD$

Accept a POSIX pkg-config command with arguments from Meson.

--- giscanner/pkgconfig.py.orig
+++ giscanner/pkgconfig.py
@@ -27,7 +27,15 @@
 
 def check_output(flags, ignore_errors, command=None):
     if command is None:
-        command = [os.environ.get('PKG_CONFIG', 'pkg-config')]
+        value = os.environ.get('PKG_CONFIG', 'pkg-config')
+        # Meson can provide a shell-quoted argv; preserve an existing path
+        # containing spaces as a single executable for compatibility.
+        try:
+            command = [value] if os.name == 'nt' or os.path.isfile(value) else shlex.split(value)
+        except ValueError as e:
+            raise PkgConfigError('invalid PKG_CONFIG command: %s' % e) from e
+        if not command or not command[0]:
+            raise PkgConfigError('invalid PKG_CONFIG command: empty command')
     argv = command[:]
     argv.extend(flags)
     try:
