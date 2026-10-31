$NetBSD$

Use NetBSD's native OpenSSL header integration when its OS build selects
that backend. Preserve the original hcrypto interface elsewhere.
Origin: NetBSD crypto/external/bsd/heimdal/dist/include/crypto-headers.h
(AI-assisted adaptation).

--- include/crypto-headers.h.orig
+++ include/crypto-headers.h
@@ -4,6 +4,38 @@
 #ifndef PACKAGE_NAME
 #error "need config.h"
 #endif
+
+#if defined(__NetBSD__) && defined(EMBERBSD_BASE_HEIMDAL) && defined(HAVE_HCRYPTO_W_OPENSSL)
+
+
+#define OPENSSL_DES_LIBDES_COMPATIBILITY
+
+#include <openssl/evp.h>
+#include <openssl/des.h>
+#include <openssl/rc4.h>
+#include <openssl/rc2.h>
+#include <openssl/md4.h>
+#include <openssl/md5.h>
+#include <openssl/sha.h>
+#include <openssl/ui.h>
+#include <openssl/rand.h>
+#include <openssl/engine.h>
+#include <openssl/pkcs12.h>
+#include <openssl/pem.h>
+#include <openssl/hmac.h>
+#include <openssl/ec.h>
+#include <openssl/ecdsa.h>
+#include <openssl/ecdh.h>
+#if OPENSSL_VERSION_NUMBER < 0x10100000UL
+# ifndef BN_is_negative
+#  define BN_set_negative(bn, flag) ((bn)->neg=(flag)?1:0)
+#  define BN_is_negative(bn) ((bn)->neg != 0)
+# endif
+#endif
+
+#include <hcrypto/ui.h>
+
+#else
 
 #ifdef KRB5
 #include <krb5-types.h>
@@ -22,4 +54,6 @@
 #include <hcrypto/pkcs12.h>
 #include <hcrypto/hmac.h>
 
+#endif /* NetBSD OpenSSL headers */
+
 #endif /* __crypto_header__ */
