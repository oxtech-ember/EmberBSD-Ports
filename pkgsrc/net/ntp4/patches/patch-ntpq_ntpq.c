$NetBSD$

Retain the NetBSD character classification adjustment; upstream has the other fixes.
Origin: NetBSD pkgsrc; rebased by EmberBSD (AI-assisted). Upstream status: not submitted.

--- ntpq/ntpq.c.orig
+++ ntpq/ntpq.c
@@ -3783,7 +3783,7 @@
 		case SN:
 			if (!value)
 				output_raw = '?';
-			else if (isdigit(*value)) {	/* number without sign */
+			else if (isdigit(*(const unsigned char *)value)) {	/* number without sign */
 				bv[0] = '+';
 				atoascii (value, MAXVALLEN, bv+1, sizeof(bv)-1);
 				output(fp, name, bv);
