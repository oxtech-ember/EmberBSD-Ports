$NetBSD$

Keep the public ctypes layout synchronized with GumboOutput.

--- python/gumbo/gumboc.py.orig
+++ python/gumbo/gumboc.py
@@ -386,6 +386,7 @@
       ('root', _Ptr(Node)),
       # TODO(jdtang): Error type.
       ('errors', Vector),
+      ('truncated', ctypes.c_bool),
   ]
 
 @contextlib.contextmanager
