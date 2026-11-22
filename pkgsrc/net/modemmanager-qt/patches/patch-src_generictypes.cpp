$NetBSD$

Use the unsigned D-Bus fields specified by the ModemManager interfaces.
SMS Validity carries its type-specific value in a variant.
Origin: EmberBSD contributors (AI-assisted).

--- src/generictypes.cpp.orig
+++ src/generictypes.cpp
@@ -14,7 +14,7 @@
 QDBusArgument &operator<<(QDBusArgument &arg, const ModemManager::Port &port)
 {
     arg.beginStructure();
-    arg << port.name << port.type;
+    arg << port.name << static_cast<uint>(port.type);
     arg.endStructure();
     return arg;
 }
@@ -36,7 +36,7 @@
 QDBusArgument &operator<<(QDBusArgument &arg, const ModemManager::CurrentModesType &mode)
 {
     arg.beginStructure();
-    arg << mode.allowed << mode.preferred;
+    arg << mode.allowed << static_cast<uint>(mode.preferred);
     arg.endStructure();
     return arg;
 }
@@ -179,7 +179,7 @@
 QDBusArgument &operator<<(QDBusArgument &arg, const ModemManager::OmaSessionType &sessionType)
 {
     arg.beginStructure();
-    arg << sessionType.type << sessionType.id;
+    arg << static_cast<uint>(sessionType.type) << sessionType.id;
     arg.endStructure();
     return arg;
 }
@@ -221,7 +221,7 @@
 QDBusArgument &operator<<(QDBusArgument &arg, const ModemManager::ValidityPair &vp)
 {
     arg.beginStructure();
-    arg << vp.validity << vp.value;
+    arg << static_cast<uint>(vp.validity) << QDBusVariant(vp.value);
     arg.endStructure();
     return arg;
 }
@@ -230,11 +230,11 @@
 const QDBusArgument &operator>>(const QDBusArgument &arg, ModemManager::ValidityPair &vp)
 {
     uint temp1;
-    uint temp2;
-    arg.beginStructure();
-    arg >> temp1 >> temp2;
-    vp.validity = (MMSmsValidityType)temp1;
-    vp.value = temp2;
+    QDBusVariant value;
+    arg.beginStructure();
+    arg >> temp1 >> value;
+    vp.validity = static_cast<MMSmsValidityType>(temp1);
+    vp.value = value.variant().toUInt();
     arg.endStructure();
 
     return arg;
@@ -243,13 +243,13 @@
 // Marshall the UnlockRetriesMap data into a D-BUS argument
 QDBusArgument &operator<<(QDBusArgument &argument, const ModemManager::UnlockRetriesMap &unlockRetriesMap)
 {
-    argument.beginMap(QMetaType::Int, QMetaType::UInt);
+    argument.beginMap(QMetaType::UInt, QMetaType::UInt);
 
     QMapIterator<MMModemLock, uint> i(unlockRetriesMap);
     while (i.hasNext()) {
         i.next();
         argument.beginMapEntry();
-        argument << i.key() << i.value();
+        argument << static_cast<uint>(i.key()) << i.value();
         argument.endMapEntry();
     }
     argument.endMap();
@@ -263,7 +263,7 @@
     unlockRetriesMap.clear();
 
     while (!argument.atEnd()) {
-        int key;
+        uint key;
         uint value;
         argument.beginMapEntry();
         argument >> key;
