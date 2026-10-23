$NetBSD$

Replace recursive epsilon-closure traversal with a bounded worklist.
Local repair for https://github.com/westes/flex/issues/414 (CVE-2019-6293).
Authored by OpenAI Codex. Each state is queued once; normal-state barriers remain.

--- src/nfa.c.orig
+++ src/nfa.c
@@ -335,28 +335,59 @@
 
 void    mark_beginning_as_normal (int mach)
 {
+	int    *pending, count;
+
 	switch (state_type[mach]) {
 	case STATE_NORMAL:
-		/* Oh, we've already visited here. */
 		return;
-
 	case STATE_TRAILING_CONTEXT:
 		state_type[mach] = STATE_NORMAL;
-
-		if (transchar[mach] == SYM_EPSILON) {
-			if (trans1[mach] != NO_TRANSITION)
-				mark_beginning_as_normal (trans1[mach]);
-
-			if (trans2[mach] != NO_TRANSITION)
-				mark_beginning_as_normal (trans2[mach]);
-		}
 		break;
-
 	default:
 		flexerror (_
 			   ("bad state type in mark_beginning_as_normal()"));
-		break;
-	}
+		return;
+	}
+
+	if (transchar[mach] != SYM_EPSILON)
+		return;
+
+	/* Mark on insertion: each allocated NFA state enters the worklist
+	 * at most once.  The worklist cannot exceed current_mns entries.
+	 * Keep graph depth off the C call stack.
+	 */
+	pending = allocate_integer_array (current_mns);
+	count = 0;
+	pending[count++] = mach;
+
+	while (count > 0) {
+		int state = pending[--count];
+		if (transchar[state] != SYM_EPSILON)
+			continue;
+
+		for (int branch = 0; branch < 2; ++branch) {
+			int next = branch == 0 ? trans1[state] : trans2[state];
+			if (next == NO_TRANSITION)
+				continue;
+
+			switch (state_type[next]) {
+			case STATE_NORMAL:
+				break;
+			case STATE_TRAILING_CONTEXT:
+				if (count >= current_mns)
+					flexerror (_("NFA worklist overflow"));
+				state_type[next] = STATE_NORMAL;
+				pending[count++] = next;
+				break;
+			default:
+				flexerror (_
+					   ("bad state type in mark_beginning_as_normal()"));
+				break;
+			}
+		}
+	}
+
+	free (pending);
 }
 
 
