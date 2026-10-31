$NetBSD$

Keep hcrypto headers out of the NetBSD native direct OpenSSL EC path.
Origin: NetBSD crypto/external/bsd/heimdal/dist/lib/krb5/pkinit-ec.c
(EmberBSD scoped adaptation; AI-assisted).

--- lib/krb5/pkinit-ec.c.orig
+++ lib/krb5/pkinit-ec.c
@@ -73,7 +73,10 @@
 #define NO_HCRYPTO_POLLUTION
 
 #include "krb5_locl.h"
+#if !(defined(__NetBSD__) && defined(EMBERBSD_BASE_HEIMDAL) && \
+      defined(HAVE_HCRYPTO_W_OPENSSL))
 #include <hcrypto/des.h>
+#endif
 #include <cms_asn1.h>
 #include <pkcs8_asn1.h>
 #include <pkcs9_asn1.h>
