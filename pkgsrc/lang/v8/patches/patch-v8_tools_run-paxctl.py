$NetBSD$

Use an explicitly qualified NetBSD host PaX utility.
Origin: NetBSD pkgsrc Chromium and EmberBSD Ports Electron overlay.
GN invokes this script with its selected Python interpreter.

--- /dev/null
+++ tools/run-paxctl.py
@@ -0,0 +1,31 @@
+# Copyright 2014 the V8 project authors. All rights reserved.
+# Use of this source code is governed by a BSD-style license that can be
+# found in the LICENSE file.
+
+"""Run the qualified NetBSD host PaX utility for a V8 build tool."""
+
+import os
+import subprocess
+import sys
+import tempfile
+
+if len(sys.argv) < 3:
+  sys.exit(2)
+stamp = sys.argv[1]
+try:
+  os.unlink(stamp)
+except FileNotFoundError:
+  pass
+if not os.path.isabs(sys.argv[2]):
+  print("paxctl needs an absolute selected host executable path", file=sys.stderr)
+  sys.exit(2)
+result = subprocess.call(sys.argv[2:])
+if result:
+  sys.exit(result)
+fd, temporary = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(stamp)))
+try:
+  os.close(fd)
+  os.replace(temporary, stamp)
+finally:
+  if os.path.exists(temporary):
+    os.unlink(temporary)
