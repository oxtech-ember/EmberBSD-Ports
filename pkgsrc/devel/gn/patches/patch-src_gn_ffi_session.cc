$NetBSD$

Use the shared CXX bridge without changing GN value semantics.
Origin: EmberBSD (AI-assisted).

--- src/gn/ffi/session.cc.orig
+++ src/gn/ffi/session.cc
@@ -65,12 +65,15 @@
                 "Arguments to load must be valid identifiers.");
       return false;
     }
-    keys_slice.push_back(rust::Str(StringAtom(val_str).str()));
+    auto interned_key = StringAtom(val_str).str();
+    keys_slice.push_back(rust::Str(interned_key.data(), interned_key.size()));
   }
 
+  auto label_value = std::string_view(label.string_value());
+  auto source_dir = dest_scope.GetSourceDir().SourceWithNoTrailingSlash();
   session.load_values(
-      rust::Str(label.string_value()),
-      rust::Str(dest_scope.GetSourceDir().SourceWithNoTrailingSlash()),
+      rust::Str(label_value.data(), label_value.size()),
+      rust::Str(source_dir.data(), source_dir.size()),
       rust::Slice<const rust::Str>(keys_slice), dest_scope,
       *dest_scope.settings(), parse_node, err);
 
