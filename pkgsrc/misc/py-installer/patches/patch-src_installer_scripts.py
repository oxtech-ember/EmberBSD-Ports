$NetBSD$

Report an unavailable optional Windows launcher through the public Script API.

--- src/installer/scripts.py.orig
+++ src/installer/scripts.py
@@ -75,7 +75,12 @@
         except KeyError:
             error = f"{key!r} not in {sorted(_ALLOWED_LAUNCHERS)!r}"
             raise InvalidScript(error) from None
-        return (files(_scripts) / name).read_bytes()
+        try:
+            return (files(_scripts) / name).read_bytes()
+        except FileNotFoundError as exc:
+            raise InvalidScript(
+                f"{kind} launcher requires the windows-launchers package option"
+            ) from exc
 
     def _get_alternate_executable(self, executable: str, kind: "LauncherKind") -> str:
         """Get an alternate executable for the launcher.
