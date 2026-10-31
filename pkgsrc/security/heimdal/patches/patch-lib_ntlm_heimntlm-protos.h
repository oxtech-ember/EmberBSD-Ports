$NetBSD$

Use checked NTLM crypto contexts in the native NetBSD backend; propagate
crypto errors through the checked NTLM session API. Update ABI version.
Origin: NetBSD crypto/external/bsd/heimdal with EmberBSD lifecycle and API fixes.

--- lib/ntlm/heimntlm-protos.h
+++ lib/ntlm/heimntlm-protos.h
@@ -183,7 +183,7 @@
 	int /*ucs2*/,
 	struct ntlm_type3 */*type3*/);
 
-void
+int
 heim_ntlm_derive_ntlm2_sess (
 	const unsigned char sessionkey[16],
 	const unsigned char */*clnt_nonce*/,
