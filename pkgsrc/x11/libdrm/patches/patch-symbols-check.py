Origin: EmberBSD; AI-assisted adaptation of the libdrm 2.4.134 test.
Status: local; not submitted upstream.

NetBSD/aarch64's ELF linker exports the same bookkeeping symbols already
excluded on Linux. Apply the existing explicit allowlist, preserving checks
for missing API symbols and unknown non-platform exports.+
--- symbols-check.py.orig
+++ symbols-check.py
@@ -38,7 +38,7 @@ def get_symbols(nm, lib):
         if len(fields) == 2 or fields[1] == 'U':
             continue
         symbol_name = fields[0]
-        if platform_name == 'Linux':
+        if platform_name in ('Linux', 'NetBSD'):
             if symbol_name in PLATFORM_SYMBOLS:
                 continue
         elif platform_name == 'Darwin':
