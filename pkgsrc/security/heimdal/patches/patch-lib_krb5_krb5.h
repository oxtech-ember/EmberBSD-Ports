$NetBSD$

Keep the public header's sibling includes relative to its installed namespace.
This supports both the package's include/krb5 layout and the OS compatibility
header which enters through /usr/include/krb5.h.

--- lib/krb5/krb5.h.orig
+++ lib/krb5/krb5.h
@@ -39,14 +39,14 @@
 #define __KRB5_H__
 
 #include <time.h>
-#include <krb5-types.h>
-
-#include <asn1_err.h>
-#include <krb5_err.h>
-#include <heim_err.h>
-#include <k524_err.h>
-
-#include <krb5_asn1.h>
+#include "krb5-types.h"
+
+#include "asn1_err.h"
+#include "krb5_err.h"
+#include "heim_err.h"
+#include "k524_err.h"
+
+#include "krb5_asn1.h"
 
 /* name confusion with MIT */
 #ifndef KRB5KDC_ERR_KEY_EXP
@@ -964,7 +964,7 @@
 
 struct hx509_certs_data;
 
-#include <krb5-protos.h>
+#include "krb5-protos.h"
 
 /* variables */
 
