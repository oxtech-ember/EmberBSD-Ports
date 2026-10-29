$NetBSD$

Preserve Qt Markdown feature semantics with md4c 0.6 (EmberBSD, AI-assisted).

--- src/gui/text/qtextmarkdownimporter.cpp.orig
+++ src/gui/text/qtextmarkdownimporter.cpp
@@ -52,7 +52,8 @@
 static_assert(int(QTextMarkdownImporter::FeatureNoHTML) == MD_FLAG_NOHTML);
 static_assert(int(QTextMarkdownImporter::DialectCommonMark) == MD_DIALECT_COMMONMARK);
 static_assert(int(QTextMarkdownImporter::DialectGitHub) ==
-              (MD_DIALECT_GITHUB | MD_FLAG_UNDERLINE | QTextMarkdownImporter::FeatureFrontMatter));
+              (MD_FLAG_PERMISSIVEAUTOLINKS | MD_FLAG_TABLES | MD_FLAG_STRIKETHROUGH |
+               MD_FLAG_TASKLISTS | MD_FLAG_UNDERLINE | QTextMarkdownImporter::FeatureFrontMatter));
 
 // --------------------------------------------------------
 // MD4C callback function wrappers
@@ -167,7 +168,7 @@
 {
     MD_PARSER callbacks = {
         0, // abi_version
-        unsigned(m_features),
+        unsigned(m_features) & ~unsigned(QTextMarkdownImporter::FeatureFrontMatter),
         &CbEnterBlock,
         &CbLeaveBlock,
         &CbEnterSpan,
