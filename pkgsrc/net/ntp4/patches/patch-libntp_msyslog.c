$NetBSD$

Preserve the NetBSD format-preserving syslog adapter.
Origin: NetBSD NTP maintenance; adapted by EmberBSD (AI-assisted).
Upstream status: not submitted.

--- libntp/msyslog.c.orig
+++ libntp/msyslog.c
@@ -42,11 +42,14 @@
 
 /* Declare the local functions */
 void	addto_syslog	(int, const char *);
-#ifndef VSNPRINTF_PERCENT_M
-void	format_errmsg	(char *, size_t, const char *, int);
+#ifdef VSNPRINTF_PERCENT_M
+#define format_errmsg(buf, len, fmt, error) (fmt)
+#else
+static const char *format_errmsg(char *, size_t, const char *, int)
+    NTP_FORMAT_ARG(3);
 
 /* format_errmsg() is under #ifndef VSNPRINTF_PERCENT_M above */
-void
+static const char *
 format_errmsg(
 	char *		nfmt,
 	size_t		lennfmt,
@@ -84,6 +87,7 @@
 		}
 	}
 	*n = '\0';
+	return nfmt;
 }
 #endif	/* VSNPRINTF_PERCENT_M */
 
@@ -231,9 +235,7 @@
 	)
 {
 #ifndef VSNPRINTF_PERCENT_M
-	char		nfmt[256];
-#else
-	const char *	nfmt = fmt;
+	char		fmtbuf[256];
 #endif
 	int		errval;
 
@@ -246,12 +248,11 @@
 #endif /* SYS_WINNT */
 		errval = errno;
 
-#ifndef VSNPRINTF_PERCENT_M
-	format_errmsg(nfmt, sizeof(nfmt), fmt, errval);
-#else
+#ifdef VSNPRINTF_PERCENT_M
 	errno = errval;
 #endif
-	return vsnprintf(buf, bufsiz, nfmt, ap);
+	return vsnprintf(buf, bufsiz,
+	    format_errmsg(fmtbuf, sizeof(fmtbuf), fmt, errval), ap);
 }
 
 
@@ -263,9 +264,7 @@
 	)
 {
 #ifndef VSNPRINTF_PERCENT_M
-	char		nfmt[256];
-#else
-	const char *	nfmt = fmt;
+	char		fmtbuf[256];
 #endif
 	int		errval;
 
@@ -278,12 +277,11 @@
 #endif /* SYS_WINNT */
 		errval = errno;
 
-#ifndef VSNPRINTF_PERCENT_M
-	format_errmsg(nfmt, sizeof(nfmt), fmt, errval);
-#else
+#ifdef VSNPRINTF_PERCENT_M
 	errno = errval;
 #endif
-	return vfprintf(fp, nfmt, ap);
+	return vfprintf(fp, 
+	    format_errmsg(fmtbuf, sizeof(fmtbuf), fmt, errval), ap);
 }
 
 
