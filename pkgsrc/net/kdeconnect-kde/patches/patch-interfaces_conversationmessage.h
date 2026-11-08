$NetBSD$

Qt 6.12 QList needs a complete element type. Define the address and attachment types first.

--- interfaces/conversationmessage.h.orig
+++ interfaces/conversationmessage.h
@@ -11,8 +11,51 @@
 
 #include "kdeconnectinterfaces_export.h"
 
-class ConversationAddress;
-class Attachment;
+class KDECONNECTINTERFACES_EXPORT ConversationAddress
+{
+public:
+    ConversationAddress(QString address = QString());
+
+    QString address() const
+    {
+        return m_address;
+    }
+
+private:
+    QString m_address;
+};
+
+class KDECONNECTINTERFACES_EXPORT Attachment
+{
+public:
+    Attachment()
+    {
+    }
+    Attachment(qint64 prtID, QString mimeType, QString base64EncodedFile, QString uniqueIdentifier);
+
+    qint64 partID() const
+    {
+        return m_partID;
+    }
+    QString mimeType() const
+    {
+        return m_mimeType;
+    }
+    QString base64EncodedFile() const
+    {
+        return m_base64EncodedFile;
+    }
+    QString uniqueIdentifier() const
+    {
+        return m_uniqueIdentifier;
+    }
+
+private:
+    qint64 m_partID; // Part ID of the attachment of the message
+    QString m_mimeType; // Type of attachment (image, video, audio etc.)
+    QString m_base64EncodedFile; // Base64 encoded string of a file
+    QString m_uniqueIdentifier; // unique name of the attachment
+};
 
 class KDECONNECTINTERFACES_EXPORT ConversationMessage
 {
@@ -179,52 +222,6 @@
     QList<Attachment> m_attachments;
 };
 
-class KDECONNECTINTERFACES_EXPORT ConversationAddress
-{
-public:
-    ConversationAddress(QString address = QString());
-
-    QString address() const
-    {
-        return m_address;
-    }
-
-private:
-    QString m_address;
-};
-
-class KDECONNECTINTERFACES_EXPORT Attachment
-{
-public:
-    Attachment()
-    {
-    }
-    Attachment(qint64 prtID, QString mimeType, QString base64EncodedFile, QString uniqueIdentifier);
-
-    qint64 partID() const
-    {
-        return m_partID;
-    }
-    QString mimeType() const
-    {
-        return m_mimeType;
-    }
-    QString base64EncodedFile() const
-    {
-        return m_base64EncodedFile;
-    }
-    QString uniqueIdentifier() const
-    {
-        return m_uniqueIdentifier;
-    }
-
-private:
-    qint64 m_partID; // Part ID of the attachment of the message
-    QString m_mimeType; // Type of attachment (image, video, audio etc.)
-    QString m_base64EncodedFile; // Base64 encoded string of a file
-    QString m_uniqueIdentifier; // unique name of the attachment
-};
-
 inline QDBusArgument &operator<<(QDBusArgument &argument, const ConversationMessage &message)
 {
     argument.beginStructure();
