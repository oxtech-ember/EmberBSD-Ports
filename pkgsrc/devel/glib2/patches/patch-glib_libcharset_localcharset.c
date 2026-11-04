$NetBSD$

Resolve NetBSD codeset names without a charset.alias file.
nl_langinfo(CODESET) gives "646" in the C locale. GNU libiconv does not
know this name, and libiconv 1.16 and later install no charset.alias.
Then GLib cannot convert command line arguments in the C locale.
Use the NetBSD table of the current gnulib localcharset.c (FSF, LGPL).
The canonical names are valid for GNU libiconv and for the base iconv.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- glib/libcharset/localcharset.c.orig
+++ glib/libcharset/localcharset.c
@@ -111,7 +111,7 @@
   cp = charset_aliases;
   if (cp == NULL)
     {
-#if !(defined VMS || defined WIN32_NATIVE || defined __CYGWIN__)
+#if !(defined VMS || defined WIN32_NATIVE || defined __CYGWIN__ || defined __NetBSD__)
       FILE *fp;
       const char *dir;
       const char *base = "charset.alias";
@@ -233,6 +233,27 @@
 	   "DECKOREAN" "\0" "EUC-KR" "\0";
 # endif
 
+# if defined __NetBSD__
+      /* GNU libiconv 1.16 and later install no charset.alias file, and
+	 nl_langinfo (CODESET) gives NetBSD names such as "646" in the C
+	 locale.  Inline the NetBSD aliases of the current gnulib
+	 localcharset.c, so that every iconv gets a GNU canonical name.  */
+      cp = "646" "\0" "ASCII" "\0"
+	   "Big5-HKSCS" "\0" "BIG5-HKSCS" "\0"
+	   "ISO8859-1" "\0" "ISO-8859-1" "\0"
+	   "ISO8859-13" "\0" "ISO-8859-13" "\0"
+	   "ISO8859-15" "\0" "ISO-8859-15" "\0"
+	   "ISO8859-2" "\0" "ISO-8859-2" "\0"
+	   "ISO8859-4" "\0" "ISO-8859-4" "\0"
+	   "ISO8859-5" "\0" "ISO-8859-5" "\0"
+	   "ISO8859-7" "\0" "ISO-8859-7" "\0"
+	   "SJIS" "\0" "SHIFT_JIS" "\0"
+	   "eucCN" "\0" "GB2312" "\0"
+	   "eucJP" "\0" "EUC-JP" "\0"
+	   "eucKR" "\0" "EUC-KR" "\0"
+	   "eucTW" "\0" "EUC-TW" "\0";
+# endif
+
 # if defined WIN32_NATIVE || defined __CYGWIN__
       /* To avoid the troubles of installing a separate file in the same
 	 directory as the DLL and of retrieving the DLL's directory at
