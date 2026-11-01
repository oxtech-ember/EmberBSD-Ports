Not submitted upstream. Avoid invalidating unchanged software layer geometry.

--- src/quick/scenegraph/adaptations/software/qsgsoftwareinternalimagenode.cpp
+++ src/quick/scenegraph/adaptations/software/qsgsoftwareinternalimagenode.cpp
@@ -385,7 +385,8 @@
     QSGLayer *t = qobject_cast<QSGLayer *>(m_texture);
     if (t) {
         doDirty = t->updateTexture();
-        markDirty(DirtyGeometry);
+        if (doDirty)
+            markDirty(DirtyGeometry);
     }
     if (doDirty)
         markDirty(DirtyMaterial);
