$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/main/ublock-brand-resource.js
+++ src/main/ublock-brand-resource.js
@@ -4,6 +4,6 @@
 // references this exact image endpoint; no HTML, scripts or IPC are exposed.
 const UBLOCK_BRAND_URL = 'blanc://ubo-brand/sunrise.png';
 function ublockBrandResourcePath(rawUrl) {
-  return rawUrl === UBLOCK_BRAND_URL ? path.join(__dirname, '../renderer/sunrise-hero-mark.png') : null;
+  return rawUrl === UBLOCK_BRAND_URL ? path.join(__dirname, '../renderer/pages/ember-browser.png') : null;
 }
 module.exports = { UBLOCK_BRAND_URL, ublockBrandResourcePath };
