$NetBSD$

Origin: EmberBSD contributors (AI-assisted).
Describe the selected native Node source-map hook.

--- README.md.orig
+++ README.md
@@ -1379,7 +1379,7 @@
 
 ## Stack traces
 
-In the terser CLI we use [source-map-support](https://npmjs.com/source-map-support) to produce good error stacks. In your own app, you're expected to enable source-map-support (read their docs) to have nice stack traces that will help you write good issues.
+This Ports build of the Terser CLI enables Node.js native source-map support for error stacks. In your own Node.js application, use `--enable-source-maps` or `process.setSourceMapsEnabled(true)` to enable mapped stack traces.
 
 <!-- REPORTING_ISSUES:END -->
 
