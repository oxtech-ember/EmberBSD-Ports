$NetBSD$

Origin: upstream BoringSSL source generator, adjusted for Electron
RIPEMD-160 compatibility by EmberBSD (AI-assisted).

diff --git gen/sources.bzl gen/sources.bzl
index 6404ca2..9708dba 100644
--- gen/sources.bzl
+++ gen/sources.bzl
@@ -533,6 +533,9 @@ crypto_sources = [
     "crypto/x509/x_x509.cc",
     "crypto/x509/x_x509a.cc",
     "crypto/xwing/xwing.cc",
+    "decrepit/blowfish/blowfish.cc",
+    "decrepit/cfb/cfb.cc",
+    "decrepit/ripemd/ripemd.cc",
     "gen/crypto/err_data.cc",
 ]
 
@@ -1222,10 +1225,8 @@ crypto_test_data = [
 
 decrepit_sources = [
     "decrepit/bio/base64_bio.cc",
-    "decrepit/blowfish/blowfish.cc",
     "decrepit/cast/cast.cc",
     "decrepit/cast/cast_tables.cc",
-    "decrepit/cfb/cfb.cc",
     "decrepit/des/cfb64ede.cc",
     "decrepit/dh/dh_decrepit.cc",
     "decrepit/dsa/dsa_decrepit.cc",
@@ -1233,7 +1234,6 @@ decrepit_sources = [
     "decrepit/evp/evp_do_all.cc",
     "decrepit/obj/obj_decrepit.cc",
     "decrepit/rc4/rc4_decrepit.cc",
-    "decrepit/ripemd/ripemd.cc",
     "decrepit/rsa/rsa_decrepit.cc",
     "decrepit/ssl/ssl_decrepit.cc",
     "decrepit/x509/x509_decrepit.cc",
