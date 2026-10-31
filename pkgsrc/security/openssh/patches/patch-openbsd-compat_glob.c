$NetBSD$

Keep compatibility glob inputs read-only.

--- openbsd-compat/glob.c
+++ openbsd-compat/glob.c
@@ -155,7 +155,7 @@
 static int	 g_Ctoc(const Char *, char *, size_t);
 static int	 g_lstat(Char *, struct stat *, glob_t *);
 static DIR	*g_opendir(Char *, glob_t *);
-static Char	*g_strchr(const Char *, int);
+static const Char *g_strchr(const Char *, int);
 static int	 g_strncmp(const Char *, const char *, size_t);
 static int	 g_stat(Char *, struct stat *, glob_t *);
 static int	 glob0(const Char *, glob_t *, struct glob_lim *);
@@ -185,7 +185,7 @@
 	Char *bufnext, *bufend, patbuf[PATH_MAX];
 	struct glob_lim limit = { 0, 0, 0 };
 
-	patnext = (u_char *) pattern;
+	patnext = (const u_char *)pattern;
 	if (!(flags & GLOB_APPEND)) {
 		pglob->gl_pathc = 0;
 		pglob->gl_pathv = NULL;
@@ -426,7 +426,7 @@
 	int rv = 0;
 
 	while (n--) {
-		rv = *(Char *)s1 - *(const unsigned char *)s2++;
+		rv = *s1 - *(const unsigned char *)s2++;
 		if (rv)
 			break;
 		if (*s1++ == '\0')
@@ -596,7 +596,7 @@
 static int
 compare(const void *p, const void *q)
 {
-	return(strcmp(*(char **)p, *(char **)q));
+	return(strcmp(*(char * const *)p, *(char * const *)q));
 }
 
 static int
@@ -1033,12 +1033,12 @@
 	return(stat(buf, sb));
 }
 
-static Char *
+static const Char *
 g_strchr(const Char *str, int ch)
 {
 	do {
 		if (*str == ch)
-			return ((Char *)str);
+			return (str);
 	} while (*str++);
 	return (NULL);
 }
