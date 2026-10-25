$NetBSD$

Validate bit-field bounds before shifts; avoid sign extension for a full word.
Origin: EmberBSD; AI-assisted local patch, not submitted upstream.

--- Source/Marine/Message.h.orig
+++ Source/Marine/Message.h
@@ -196,7 +196,7 @@
 
 		unsigned getUint(int start, int len) const
 		{
-			if (start < 0 || start + len > MAX_AIS_LENGTH)
+			if (len < 1 || len > 32 || start < 0 || start > MAX_AIS_LENGTH - len)
 				return 0;
 
 			// Branchless: 5-byte big-endian load covers any len<=32 with y<=7 (max 39 bits).
@@ -217,9 +217,11 @@
 
 		int getInt(int start, int len) const
 		{
+			if (len < 1 || len > 32)
+				return 0;
 			const unsigned ones = ~0u;
 			unsigned u = getUint(start, len);
-			if (u & (1u << (len - 1)))
+			if (len < 32 && (u & (1u << (len - 1))))
 				u |= ones << len;
 			return (int)u;
 		}
