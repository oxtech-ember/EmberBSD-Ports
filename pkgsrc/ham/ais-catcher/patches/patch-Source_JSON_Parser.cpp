$NetBSD$

Use the input cursor for escaped-string errors when tokenStart is null.
Origin: EmberBSD; AI-assisted local patch, not submitted upstream.

--- Source/JSON/Parser.cpp.orig
+++ Source/JSON/Parser.cpp
@@ -421,7 +421,7 @@
 
 	[[noreturn]] void Parser::error_parser(const std::string &err, bool syntax)
 	{
-		error(err, (int)(tokenStart - p_start), syntax);
+		error(err, (int)((tokenStart ? tokenStart : p) - p_start), syntax);
 	}
 
 	std::string Parser::tokenString() const
