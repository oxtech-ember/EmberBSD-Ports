$NetBSD$

Select input formats and preserve native resource forks safely.

--- a/Rez/README.md
+++ b/Rez/README.md
@@ -3,10 +3,18 @@
 
 A reimplementation of the classic Rez resource compiler.
 
+`--input-format=auto` retains extension-based input detection. Use `text`
+or `binary` to select one format for all input files explicitly.
+
+On macOS, `--resource-fork-only --append -o FILE` merges resources into the
+native resource fork of an existing regular file. Data and Finder information
+are left alone. Compilation and fork validation finish before the fork is
+written. Other hosts reject this mode. The option cannot be combined with
+`--data`, `--cc`, `--type`, or `--creator`.
+
 
 Known Bugs & Limitations
 -----------------
 
 * `$ABCD` alternate syntax for hex numbers is not supported
-* hex strings not supported
 * Other than in Apple Rez, the preprocessor is case sensitive.
