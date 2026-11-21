$NetBSD$

Preserve litehtml 0.10's public string alias for existing consumers.

--- litehtml/include/litehtml/types.h.orig
+++ litehtml/include/litehtml/types.h
@@ -20,6 +20,7 @@
     class document;
     class element;
 
+    using string        = std::string;
     using string_map    = std::map<std::string, std::string>;
     using elements_list = std::list<std::shared_ptr<element>>;
     using int_vector    = std::vector<int>;
