$NetBSD$

Use the common libpsl rule data and preserve Qt suffix policy.

--- src/network/kernel/qtldurl.cpp.orig
+++ src/network/kernel/qtldurl.cpp
@@ -6,6 +6,24 @@
 
 #if QT_CONFIG(topleveldomain)
 
+#if QT_CONFIG(publicsuffix_libpsl)
+#include "QtCore/qbytearray.h"
+#include "QtCore/qstring.h"
+#include <libpsl.h>
+QT_BEGIN_NAMESPACE
+static constexpr int PSL_NOT_FOUND = -1;
+static constexpr int PSL_FLAG_EXCEPTION = PSL_RULE_EXCEPTION;
+static constexpr int PSL_FLAG_WILDCARD = PSL_RULE_WILDCARD;
+class QPublicSuffixDatabase final
+{
+public:
+    int lookupDomain(QByteArrayView domain) const
+    {
+        return psl_lookup_rule(psl_builtin(), domain.data(), domain.size());
+    }
+};
+static const QPublicSuffixDatabase m_publicSuffix;
+#else
 #include "QtCore/qfile.h"
 #include "QtCore/qloggingcategory.h"
 #include "QtCore/qstandardpaths.h"
@@ -169,6 +187,7 @@
 static const QPublicSuffixDatabase m_publicSuffix;
 
 #endif // QT_CONFIG(publicsuffix_system)
+#endif // QT_CONFIG(publicsuffix_libpsl)
 
 /*!
     \internal
