$NetBSD$

Origin: upstream BoringSSL source generator, adjusted for Electron
RIPEMD-160 compatibility by EmberBSD (AI-assisted).

diff --git gen/sources.mk gen/sources.mk
index 1721bfc..53030c9 100644
--- gen/sources.mk
+++ gen/sources.mk
@@ -525,6 +525,9 @@ boringssl_crypto_sources := \
   crypto/x509/x_x509.cc \
   crypto/x509/x_x509a.cc \
   crypto/xwing/xwing.cc \
+  decrepit/blowfish/blowfish.cc \
+  decrepit/cfb/cfb.cc \
+  decrepit/ripemd/ripemd.cc \
   gen/crypto/err_data.cc
 
 boringssl_crypto_headers := \
@@ -1206,10 +1209,8 @@ boringssl_crypto_test_data := \
 
 boringssl_decrepit_sources := \
   decrepit/bio/base64_bio.cc \
-  decrepit/blowfish/blowfish.cc \
   decrepit/cast/cast.cc \
   decrepit/cast/cast_tables.cc \
-  decrepit/cfb/cfb.cc \
   decrepit/des/cfb64ede.cc \
   decrepit/dh/dh_decrepit.cc \
   decrepit/dsa/dsa_decrepit.cc \
@@ -1217,7 +1218,6 @@ boringssl_decrepit_sources := \
   decrepit/evp/evp_do_all.cc \
   decrepit/obj/obj_decrepit.cc \
   decrepit/rc4/rc4_decrepit.cc \
-  decrepit/ripemd/ripemd.cc \
   decrepit/rsa/rsa_decrepit.cc \
   decrepit/ssl/ssl_decrepit.cc \
   decrepit/x509/x509_decrepit.cc \
