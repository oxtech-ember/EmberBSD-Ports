$NetBSD$

Refresh the existing pkgsrc platform adaptation for WebKitGTK 2.54.1.
Origin: EmberBSD (AI-assisted), based on the pinned pkgsrc patch; not submitted upstream.

--- Source/WebCore/rendering/RenderBox.h.orig
+++ Source/WebCore/rendering/RenderBox.h
@@ -661,7 +661,7 @@
 
     void constrainIntrinsicLogicalWidthsByMinMax(LayoutUnit& minIntrinsicLogicalWidth, LayoutUnit& maxIntrinsicLogicalWidth) const;
 
-    bool isAspectRatioDegenerate(double aspectRatio) const { return !aspectRatio || isnan(aspectRatio); }
+    bool isAspectRatioDegenerate(double aspectRatio) const { return !aspectRatio || std::isnan(aspectRatio); }
 
     LayoutUnit fillAvailableMeasure(LayoutUnit availableLogicalWidth) const;
     LayoutUnit fillAvailableMeasure(LayoutUnit availableLogicalWidth, LayoutUnit& marginStart, LayoutUnit& marginEnd) const;
