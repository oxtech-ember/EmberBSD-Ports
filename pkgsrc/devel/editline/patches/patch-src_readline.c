$NetBSD$

Release generated readline completions after an allocation failure.
Local EmberBSD Ports fix, prepared with AI assistance. Not submitted upstream.
Regression: files/completion-oom.c readline, linked against the static library.

--- src/readline.c.orig
+++ src/readline.c
@@ -2446,6 +2446,8 @@ rl_completion_matches(const char *str, rl
 	return list;
 
 out:
+	for (i = 1; i < len; i++)
+		el_free(list[i]);
 	el_free(list);
 	return NULL;
 }
