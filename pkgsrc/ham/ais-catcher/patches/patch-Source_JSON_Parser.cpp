$NetBSD$

Use the input cursor for escaped-string errors when tokenStart is null.
Origin: EmberBSD; AI-assisted local patch, not submitted upstream.

--- Source/JSON/Parser.cpp.orig
+++ Source/JSON/Parser.cpp
@@ -353,7 +353,7 @@
 
 	[[noreturn]] void Parser::error_parser(const std::string &err)
 	{
-		error(err, (int)(tokenStart - p_start));
+		error(err, (int)((tokenStart ? tokenStart : p) - p_start));
 	}
 
 	std::string Parser::tokenString() const
