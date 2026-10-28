$NetBSD$

Origin: upstream BoringSSL source generator, adjusted for Electron
RIPEMD-160 compatibility by EmberBSD (AI-assisted).

diff --git gen/sources.cmake gen/sources.cmake
index af59729..38f6056 100644
--- gen/sources.cmake
+++ gen/sources.cmake
@@ -551,6 +551,9 @@ set(
   crypto/x509/x_x509.cc
   crypto/x509/x_x509a.cc
   crypto/xwing/xwing.cc
+  decrepit/blowfish/blowfish.cc
+  decrepit/cfb/cfb.cc
+  decrepit/ripemd/ripemd.cc
   gen/crypto/err_data.cc
 )
 
@@ -1256,10 +1259,8 @@ set(
   DECREPIT_SOURCES
 
   decrepit/bio/base64_bio.cc
-  decrepit/blowfish/blowfish.cc
   decrepit/cast/cast.cc
   decrepit/cast/cast_tables.cc
-  decrepit/cfb/cfb.cc
   decrepit/des/cfb64ede.cc
   decrepit/dh/dh_decrepit.cc
   decrepit/dsa/dsa_decrepit.cc
@@ -1267,7 +1268,6 @@ set(
   decrepit/evp/evp_do_all.cc
   decrepit/obj/obj_decrepit.cc
   decrepit/rc4/rc4_decrepit.cc
-  decrepit/ripemd/ripemd.cc
   decrepit/rsa/rsa_decrepit.cc
   decrepit/ssl/ssl_decrepit.cc
   decrepit/x509/x509_decrepit.cc
