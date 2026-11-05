# $NetBSD$

Apply the Telegram block quote limit through the shared cmark parser API.

--- Telegram/SourceFiles/iv/markdown/iv_markdown_parse_convert.cpp.orig
+++ Telegram/SourceFiles/iv/markdown/iv_markdown_parse_convert.cpp
@@ -695,6 +695,7 @@
 		return nullptr;
 	}
 	cmark_parser_set_allocation_abort_flag(parser, abortFlag);
+	cmark_parser_set_max_block_quote_depth(parser, 512);
 	for (const auto name : kExtensions) {
 		const auto extension = cmark_find_syntax_extension(name);
 		if (!extension
