$NetBSD$

Release every generated completion when allocating the result array fails.
Both array growth and common-prefix allocation can fail after strings exist.
Local EmberBSD Ports fix, prepared with AI assistance. Not submitted upstream.
Regression: files/completion-oom.c, linked against the actual static library.

--- src/filecomplete.c.orig
+++ src/filecomplete.c
@@ -476,8 +476,8 @@ completion_matches(const char *text, char
 			nmatch_list = el_realloc(match_list,
 			    match_list_len * sizeof(*nmatch_list));
 			if (nmatch_list == NULL) {
-				el_free(match_list);
-				return NULL;
+				el_free(retstr);
+				goto nomem;
 			}
 			match_list = nmatch_list;
 
@@ -501,10 +501,8 @@ completion_matches(const char *text, char
 	}
 
 	retstr = el_calloc(max_equal + 1, sizeof(*retstr));
-	if (retstr == NULL) {
-		el_free(match_list);
-		return NULL;
-	}
+	if (retstr == NULL)
+		goto nomem;
 	(void)strlcpy(retstr, match_list[1], max_equal + 1);
 	match_list[0] = retstr;
 
@@ -512,6 +510,12 @@ completion_matches(const char *text, char
 	match_list[matches + 1] = NULL;
 
 	return match_list;
+
+nomem:
+	for (i = 1; i <= matches; i++)
+		el_free(match_list[i]);
+	el_free(match_list);
+	return NULL;
 }
 
 /*
