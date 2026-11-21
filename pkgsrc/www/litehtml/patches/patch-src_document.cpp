$NetBSD$

Origin: upstream Twidget Telegram Desktop 7.4.4 pinned submodule; common litehtml package integration.

--- litehtml/src/document.cpp.orig
+++ litehtml/src/document.cpp
@@ -27,7 +27,7 @@
 #include "el_text.h"
 #include "el_title.h"
 #include "el_tr.h"
-#include "gumbo.h"
+#include <gumbo.h>
 #include "html_tag.h"
 #include "render_block.h"
 #include "render_item.h"
@@ -48,6 +48,17 @@
 namespace litehtml
 {
 
+    namespace
+    {
+        constexpr GumboLimits kWidgetGumboLimits{400, 1U << 20};
+
+        GumboOutput* parse_document_html(const GumboOptions* options, const char* text, size_t length, bool bounded)
+        {
+            return bounded ? gumbo_parse_with_limits(options, text, length, &kWidgetGumboLimits)
+                           : gumbo_parse_with_options(options, text, length);
+        }
+    }
+
     document::document(document_container* container)
     {
         m_container = container;
@@ -73,12 +84,20 @@
     document::ptr document::createFromString(const estring& str, document_container* container,
                                              const std::string& master_styles, const std::string& user_styles)
     {
+        return createFromString(str, container, master_styles, user_styles, parse_mode::standard);
+    }
+
+    document::ptr document::createFromString(const estring& str, document_container* container,
+                                             const std::string& master_styles, const std::string& user_styles,
+                                             parse_mode mode)
+    {
         // Create litehtml::document
         document::ptr doc = std::make_shared<document>(container);
+        doc->m_bounded_widget = mode == parse_mode::bounded_widget;
 
         // Parse document into GumboOutput
         GumboOutput* output = doc->parse_html(str);
-        if(output->truncated)
+        if(doc->m_bounded_widget && output->truncated)
         {
             container->sanitizer_limit("elements");
             doc->m_build_limited = true;
@@ -118,10 +137,17 @@
     document::ptr document::createUpdatableFromString(const std::string& html, document_container* container,
                                                       const std::string& master_styles)
     {
+        return createUpdatableFromString(html, container, master_styles, parse_mode::standard);
+    }
+
+    document::ptr document::createUpdatableFromString(const std::string& html, document_container* container,
+                                                      const std::string& master_styles, parse_mode mode)
+    {
         document::ptr doc = std::make_shared<document>(container);
+        doc->m_bounded_widget = mode == parse_mode::bounded_widget;
         doc->m_text        = html;
-        GumboOutput* output = gumbo_parse_with_options(&kGumboDefaultOptions, doc->m_text.data(), doc->m_text.size());
-        if(output->truncated)
+        GumboOutput* output = parse_document_html(&kGumboDefaultOptions, doc->m_text.data(), doc->m_text.size(), doc->m_bounded_widget);
+        if(doc->m_bounded_widget && output->truncated)
         {
             container->sanitizer_limit("elements");
             doc->m_build_limited = true;
@@ -1452,6 +1478,8 @@
 
     bool document::take_table_cells(int count)
     {
+        if(!m_bounded_widget)
+            return true;
         if(m_table_cells + count > max_table_cells)
         {
             if(!m_table_limited)
@@ -1467,6 +1495,8 @@
 
     bool document::take_generated(size_t bytes)
     {
+        if(!m_bounded_widget)
+            return true;
         if(m_generated_limited)
             return false;
         if(m_generated_boxes >= max_generated_boxes || bytes > max_generated_box ||
@@ -1895,7 +1925,7 @@
         const bool position_scope  = (scope & 2) != 0;
 
         std::string  text   = html;
-        GumboOutput* output = gumbo_parse_with_options(&kGumboDefaultOptions, text.data(), text.size());
+        GumboOutput* output = parse_document_html(&kGumboDefaultOptions, text.data(), text.size(), m_bounded_widget);
         if(!output)
             return false;
         auto fail = [&]() {
@@ -1906,7 +1936,7 @@
             return fail();
         int total = 0, deepest = 0;
         count_elements(output->document, 0, total, deepest);
-        if(total > max_build_elements || deepest >= max_build_depth)
+        if(m_bounded_widget && (total > max_build_elements || deepest >= max_build_depth))
             return fail();
 
         auto holes_of = [&](const GumboNode* node) -> const std::vector<size_t>* {
@@ -2725,7 +2755,7 @@
         // Instead, we parse entire file and then handle <meta> tags.
 
         // Using gumbo_parse_with_options to pass string length (m_text may contain NUL chars).
-        GumboOutput* output = gumbo_parse_with_options(&kGumboDefaultOptions, m_text.data(), m_text.size());
+        GumboOutput* output = parse_document_html(&kGumboDefaultOptions, m_text.data(), m_text.size(), m_bounded_widget);
 
         if(str.confidence == confidence::certain)
         {
@@ -2753,7 +2783,7 @@
                 {
                     decode(str, new_encoding, m_text);
                 }
-                output = gumbo_parse_with_options(&kGumboDefaultOptions, m_text.data(), m_text.size());
+                output = parse_document_html(&kGumboDefaultOptions, m_text.data(), m_text.size(), m_bounded_widget);
             }
         }
 
@@ -2790,7 +2820,7 @@
                     }
                     if(!name.empty())
                     {
-                        if(m_build_depth >= max_build_depth || m_build_elements >= max_build_elements)
+                        if(m_bounded_widget && (m_build_depth >= max_build_depth || m_build_elements >= max_build_elements))
                         {
                             m_container->sanitizer_limit(m_build_depth >= max_build_depth ? "depth" : "elements");
                             m_build_limited = true;
@@ -3844,7 +3874,12 @@
         // Although Gumbo always creates html tag anyway. We have to ignore it in create_node.
         opts.fragment_context = GUMBO_TAG_BODY;
         // parse document into GumboOutput
-        GumboOutput* output = gumbo_parse_with_options(&opts, str, strlen(str));
+        GumboOutput* output = parse_document_html(&opts, str, strlen(str), m_bounded_widget);
+        if(m_bounded_widget && output->truncated)
+        {
+            m_container->sanitizer_limit("elements");
+            m_build_limited = true;
+        }
 
         // Create litehtml::elements.
         elements_list child_elements;
