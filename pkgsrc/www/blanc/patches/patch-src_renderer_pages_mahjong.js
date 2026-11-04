$NetBSD$

Use the independent Ember Browser icon and retain upstream attribution.
Origin: EmberBSD contributors (AI-assisted).

--- src/renderer/pages/mahjong.js
+++ src/renderer/pages/mahjong.js
@@ -76,7 +76,7 @@
 const DRAGON_ART = Object.freeze({
   c: 'mahjong-dragon-red.png',
   f: 'mahjong-dragon-green.png',
-  p: 'mahjong-dragon-white.png',
+  p: 'mahjong-dragon-white-seal.png',
 });
 const DRAGON_SEAL_ART = Object.freeze({
   c: 'mahjong-dragon-red-seal.png',
@@ -254,7 +254,7 @@
   w: t('mahjong.tile.motif.moonAndWave'), n: t('mahjong.tile.motif.mountain'),
 };
 const DRAGON_MOTIFS = {
-  c: t('mahjong.tile.motif.flame'), f: t('mahjong.tile.motif.flourish'), p: t('mahjong.tile.motif.blancMark'),
+  c: t('mahjong.tile.motif.flame'), f: t('mahjong.tile.motif.flourish'), p: t('mahjong.tile.motif.seal'),
 };
 function tileName(kind) {
   const [family, id, rawVariant] = kind.split('-');
