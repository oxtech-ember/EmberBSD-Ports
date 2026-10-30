$NetBSD$

Origin: EmberBSD; AI-assisted, not submitted upstream.

Use the public Yoga 3 node API instead of the bundled C++ node class.

--- src/quicklayouts/qquickflexboxlayoutitem.cpp.orig
+++ src/quicklayouts/qquickflexboxlayoutitem.cpp
@@ -212,7 +212,7 @@
 {
     return ((YGNodeStyleGetAlignSelf(m_yogaNode) == YGAlignStretch) ||
             ((YGNodeStyleGetAlignSelf(m_yogaNode) == YGAlignAuto) &&
-             (YGNodeStyleGetAlignItems(m_yogaNode->getParent()) == YGAlignStretch)));
+             (YGNodeStyleGetAlignItems(YGNodeGetParent(m_yogaNode)) == YGAlignStretch)));
 }
 
 void QQuickFlexboxLayoutItem::inheritItemStretchAlongCrossSection()
