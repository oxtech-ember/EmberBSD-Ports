Retain the standard end-pointer result without a const-dropping cast.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- pcap.c.orig
+++ pcap.c
@@ -3901,7 +3901,7 @@
 		 */
 		*nump = 0;
 		if (endptr != NULL)
-			*endptr = (char *)cp;
+			*endptr = strchr(cp, (unsigned char)cp[0]);
 		return (EINVAL);
 	}
 
