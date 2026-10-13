$NetBSD$

Keep parsed keyboard models and option groups in the public rules result.
Append in parse order, including extras and additional rule directories.
EmberBSD change (AI-assisted), not submitted upstream.

--- src/im/keyboard/xkbrules.cpp.orig
+++ src/im/keyboard/xkbrules.cpp
@@ -159,6 +159,14 @@
                     std::make_move_iterator(info.variantInfos.end()));
             }
         }
+        rules->modelInfos_.insert(
+            rules->modelInfos_.end(),
+            std::make_move_iterator(modelInfos_.begin()),
+            std::make_move_iterator(modelInfos_.end()));
+        rules->optionGroupInfos_.insert(
+            rules->optionGroupInfos_.end(),
+            std::make_move_iterator(optionGroupInfos_.begin()),
+            std::make_move_iterator(optionGroupInfos_.end()));
     }
 };
 
