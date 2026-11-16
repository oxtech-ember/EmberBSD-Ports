$NetBSD$

RADIUS: Fix Message-Authenticator attribute validation.
Upstream: https://git.w1.fi/cgit/hostap/commit/?id=aa02cfa569477f67f3915c8b9a83d1a7ca93693d
Advisory: https://w1.fi/security/2026-5/
From: Jouni Malinen <jouni.malinen@oss.qualcomm.com>
Date: Fri, 14 Aug 2026 11:20:34 +0300
Signed-off-by: Jouni Malinen <jouni.malinen@oss.qualcomm.com>

Validate the fixed 16-byte value before copying or zeroing it in both
RADIUS verifiers. This is the unchanged upstream fix for WPA/hostapd 2.12.

--- src/radius/radius.c.orig
+++ src/radius/radius.c
@@ -695,6 +695,11 @@ int radius_msg_verify_das_req(struct radius_msg *msg, const u8 *secret,
 		return 0;
 	}
 
+	if (attr->length != sizeof(*attr) + MD5_MAC_LEN) {
+		wpa_printf(MSG_WARNING, "Invalid Message-Authenticator length");
+		return 1;
+	}
+
 	os_memcpy(orig, attr + 1, MD5_MAC_LEN);
 	os_memset(attr + 1, 0, MD5_MAC_LEN);
 	os_memcpy(orig_authenticator, msg->hdr->authenticator,
@@ -993,6 +998,11 @@ int radius_msg_verify_msg_auth(struct radius_msg *msg, const u8 *secret,
 		return 1;
 	}
 
+	if (attr->length != sizeof(*attr) + MD5_MAC_LEN) {
+		wpa_printf(MSG_INFO, "Invalid Message-Authenticator length");
+		return 1;
+	}
+
 	os_memcpy(orig, attr + 1, MD5_MAC_LEN);
 	os_memset(attr + 1, 0, MD5_MAC_LEN);
 	if (req_auth) {
