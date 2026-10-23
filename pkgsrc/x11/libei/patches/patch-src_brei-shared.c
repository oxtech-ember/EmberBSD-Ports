$NetBSD$

Origin: EmberBSD (AI-assisted).
Reject string lengths that cannot fit after the protocol header and alignment.
Check before arithmetic and return the existing protocol error before allocation.
Extend the existing arithmetic unit test without constructing network messages.

--- src/brei-shared.c.orig
+++ src/brei-shared.c
@@ -57,6 +57,10 @@
 static inline uint32_t
 brei_string_proto_length(uint32_t slen)
 {
+	/* Zero is invalid: even an empty string needs the length field. */
+	if (slen > UINT32_MAX - 7)
+		return 0;
+
 	uint32_t length = 4 + slen;
 	uint32_t protolen = (length + 3) / 4 * 4;
 	assert(protolen % 4 == 0);
@@ -254,7 +258,7 @@
 			uint32_t protolen = brei_string_proto_length(slen); /* in bytes */
 			uint32_t len32 = protolen / 4; /* p and end are uint32_t* */
 
-			if (remaining < len32) {
+			if (protolen == 0 || remaining < len32) {
 				return brei_result_new(
 					BREI_CONNECTION_DISCONNECT_REASON_PROTOCOL,
 					"Invalid string length %u, only %u bytes remaining",
@@ -520,6 +524,9 @@
 	munit_assert_int(brei_string_proto_length(8), ==, 12);
 	munit_assert_int(brei_string_proto_length(12), ==, 16);
 	munit_assert_int(brei_string_proto_length(13), ==, 20);
+	munit_assert_uint32(brei_string_proto_length(UINT32_MAX - 7), ==, UINT32_MAX - 3);
+	munit_assert_uint32(brei_string_proto_length(UINT32_MAX - 6), ==, 0);
+	munit_assert_uint32(brei_string_proto_length(UINT32_MAX), ==, 0);
 
 	return MUNIT_OK;
 }
