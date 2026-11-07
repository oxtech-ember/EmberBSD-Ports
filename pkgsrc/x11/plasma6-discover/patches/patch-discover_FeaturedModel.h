$NetBSD$

Home uses verified desktop applications for this backend.

--- discover/FeaturedModel.h.orig
+++ discover/FeaturedModel.h
@@ -18,4 +18,7 @@
     }
 
     void refresh() override;
+
+private:
+    void refreshEmberBSD();
 };
