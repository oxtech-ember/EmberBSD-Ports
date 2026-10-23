$NetBSD$

Keep history substitution buffers owned on allocation and syntax failures.
Reserve the terminator before growing a history search pattern.
Release generated readline completions after an allocation failure.
Local EmberBSD Ports fixes, prepared with AI assistance. Not submitted upstream.
Regressions: files/history-allocation.c and files/completion-oom.c.

--- src/readline.c.orig
+++ src/readline.c
@@ -695,46 +695,41 @@
 	size_t len = 0;
 	const char *cmd = *cmdp;
 	char *what = el_realloc(*fromp, size * sizeof(*what));
-	if (what == NULL){
+
+	if (what == NULL) {
 		el_free(*fromp);
 		*fromp = NULL;
 		return 0;
 	}
+	*fromp = NULL;
 	for (; *cmd && *cmd != delim; cmd++) {
 		if (*cmd == '\\' && cmd[1] == delim)
 			cmd++;
-		if (len - 1 >= size) {
+		if (len >= size - 1) {
 			char *nwhat;
-			nwhat = el_realloc(what, (size <<= 1) * sizeof(*nwhat));
-			if (nwhat == NULL) {
-				el_free(what);
-				el_free(*fromp);
-				*cmdp = cmd;
-				*fromp = NULL;
-				return 0;
-			}
+
+			if (size > SIZE_MAX / 2)
+				goto nomem;
+			nwhat = el_realloc(what, size * 2 * sizeof(*nwhat));
+			if (nwhat == NULL)
+				goto nomem;
+			size *= 2;
 			what = nwhat;
 		}
 		what[len++] = *cmd;
 	}
 	what[len] = '\0';
-	*fromp = what;
 	*cmdp = cmd;
 	if (*what == '\0') {
 		el_free(what);
-		if (search) {
-			*fromp = strdup(search);
-			if (*fromp == NULL) {
-				return 0;
-			}
-		} else {
-			*fromp = NULL;
+		if (search == NULL)
 			return -1;
-		}
+		what = strdup(search);
+		if (what == NULL)
+			return 0;
 	}
 	if (!*cmd) {
 		el_free(what);
-		*fromp = NULL;
 		return -1;
 	}
 
@@ -743,10 +738,15 @@
 
 	if (!*cmd) {
 		el_free(what);
-		*fromp = NULL;
 		return -1;
 	}
+	*fromp = what;
 	return 1;
+
+nomem:
+	el_free(what);
+	*cmdp = cmd;
+	return 0;
 }
 
 static int
@@ -757,9 +757,9 @@
 	size_t from_len = strlen(from);
 	const char *cmd = *cmdp;
 	char *with = el_realloc(*top, size * sizeof(*with));
-	*top = NULL;
 	if (with == NULL)
 		goto out;
+	*top = NULL;
 
 	for (; *cmd && *cmd != delim; cmd++) {
 		if (len + from_len + 1 >= size) {
@@ -2444,6 +2444,8 @@
 	return list;
 
 out:
+	for (i = 1; i < len; i++)
+		el_free(list[i]);
 	el_free(list);
 	return NULL;
 }
