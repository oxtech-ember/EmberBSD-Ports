$NetBSD$

libc++ wrap iterators have no public base(). The message object is *modelIt.

--- src/messagemodel.cpp.orig
+++ src/messagemodel.cpp
@@ -281,7 +281,7 @@
     Q_ASSERT(modelIt != m_messages.cend());
 
     const size_t i = (m_messages.size() - 1) - std::distance(m_messages.begin(), modelIt);
-    return qMakePair(&(*modelIt.base()), i);
+    return qMakePair(&(*modelIt), i);
 }
 
 void MessageModel::updateMessageState(const QString &id, MessageState state, const bool temp)
