--- Telegram/ThirdParty/twidget/core/src/renderer.cpp.orig
+++ Telegram/ThirdParty/twidget/core/src/renderer.cpp
@@ -818,9 +818,11 @@
         // The fork's keys are only good within a document: a new one may resolve colours differently.
         cached_.clear();
         cached_commands_ = 0;
-        doc_ = litehtml::document::createUpdatableFromString(html, this, master_css_);
+        doc_ = litehtml::document::createUpdatableFromString(
+            html, this, master_css_, litehtml::document::parse_mode::bounded_widget);
 #else
-        doc_ = litehtml::document::createFromString(litehtml::estring(html), this, master_css_);
+        doc_ = litehtml::document::createFromString(
+            litehtml::estring(html), this, master_css_, {}, litehtml::document::parse_mode::bounded_widget);
 #endif
         if (!doc_) return true;
         rendered_width_ = float(r_.width_);
