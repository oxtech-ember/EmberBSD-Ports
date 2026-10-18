$NetBSD$

Refresh the existing pkgsrc platform adaptation for WebKitGTK 2.54.1.
Origin: EmberBSD (AI-assisted), based on the pinned pkgsrc patch; not submitted upstream.

--- Source/WebCore/rendering/shapes/ShapeOutsideInfo.cpp.orig
+++ Source/WebCore/rendering/shapes/ShapeOutsideInfo.cpp
@@ -251,7 +251,7 @@
 
     auto logicalMargin = [&] {
         auto shapeMargin = Style::evaluate<LayoutUnit>(style.shapeMargin(), containingBlock.contentBoxLogicalWidth(), zoom).toFloat();
-        return isnan(shapeMargin) ? 0.0f : shapeMargin;
+        return std::isnan(shapeMargin) ? 0.0f : shapeMargin;
     }();
 
     return WTF::switchOn(shapeOutside,
