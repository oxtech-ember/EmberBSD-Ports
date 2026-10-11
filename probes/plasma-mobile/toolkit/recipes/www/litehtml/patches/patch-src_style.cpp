$NetBSD$

Origin: EmberBSD (AI-assisted), not submitted upstream.
The first keyword has a zero mask: none for decoration and over for emphasis.
Do not shift by -1 when converting that keyword to the corresponding flags.

--- src/style.cpp.orig
+++ src/style.cpp
@@ -1330,7 +1330,7 @@
 		if(token.type == IDENT)
 		{
 			int idx = value_index(token.ident(), style_text_decoration_line_strings);
-			if(idx >= 0)
+			if(idx > 0)
 			{
 				val |= 1 << (idx - 1);
 			}
@@ -1377,7 +1377,7 @@
 		if(token.type == IDENT)
 		{
 			int idx = value_index(token.ident(), style_text_emphasis_position_strings);
-			if(idx >= 0)
+			if(idx > 0)
 			{
 				val |= 1 << (idx - 1);
 			}
