$NetBSD$

Retain the litehtml 0.10 redraw-box callback overloads and expose explicit bounded widget parse mode.

--- litehtml/include/litehtml/document.h.orig
+++ litehtml/include/litehtml/document.h
@@ -55,6 +55,11 @@
     class document : public std::enable_shared_from_this<document>
     {
       public:
+        enum class parse_mode
+        {
+            standard,
+            bounded_widget
+        };
         bool take_table_cells(int count);
         bool take_generated(size_t bytes);
         void release_generated(int boxes, size_t bytes);
@@ -170,6 +175,7 @@
         int                                     m_build_depth    = 0;
         int                                     m_build_elements = 0;
         bool                                    m_build_limited  = false;
+        bool                                    m_bounded_widget = false;
         int                                     m_selector_scope = -1;
         int                                     m_ids_selectable = -1;
         int                                     m_style_attributes_selectable = -1;
@@ -273,14 +279,33 @@
         void                         add_stylesheet(const char* str, const char* baseurl, const char* media);
         bool                         on_mouse_over(pixel_t x, pixel_t y, pixel_t client_x, pixel_t client_y,
                                                    const std::function<void(const position&)>& redraw_box);
+        bool                         on_mouse_over(pixel_t x, pixel_t y, pixel_t client_x, pixel_t client_y,
+                                                   position::vector& redraw_boxes)
+        {
+            return on_mouse_over(x, y, client_x, client_y, [&redraw_boxes](const position& box) { redraw_boxes.push_back(box); });
+        }
         std::vector<scroll_values>   on_scroll(pixel_t dx, pixel_t dy, pixel_t x, pixel_t y, pixel_t client_x,
                                                pixel_t client_y) const;
         bool                         on_lbutton_down(pixel_t x, pixel_t y, pixel_t client_x, pixel_t client_y,
                                                      const std::function<void(const position&)>& redraw_box);
+        bool                         on_lbutton_down(pixel_t x, pixel_t y, pixel_t client_x, pixel_t client_y,
+                                                     position::vector& redraw_boxes)
+        {
+            return on_lbutton_down(x, y, client_x, client_y, [&redraw_boxes](const position& box) { redraw_boxes.push_back(box); });
+        }
         bool                         on_lbutton_up(pixel_t x, pixel_t y, pixel_t client_x, pixel_t client_y,
                                                    const std::function<void(const position&)>& redraw_box);
+        bool                         on_lbutton_up(pixel_t x, pixel_t y, pixel_t client_x, pixel_t client_y,
+                                                   position::vector& redraw_boxes)
+        {
+            return on_lbutton_up(x, y, client_x, client_y, [&redraw_boxes](const position& box) { redraw_boxes.push_back(box); });
+        }
         bool                         on_button_cancel(const std::function<void(const position&)>& redraw_box);
         bool                         on_mouse_leave(const std::function<void(const position&)>& redraw_box);
+        bool                         on_mouse_leave(position::vector& redraw_boxes)
+        {
+            return on_mouse_leave([&redraw_boxes](const position& box) { redraw_boxes.push_back(box); });
+        }
         std::shared_ptr<element>     create_element(const char* tag_name, const string_map& attributes);
         std::shared_ptr<element>     root();
         std::shared_ptr<render_item> root_render();
@@ -303,10 +328,15 @@
         static document::ptr createFromString(const estring& str, document_container* container,
                                               const std::string& master_styles = litehtml::master_css,
                                               const std::string& user_styles   = {});
+        static document::ptr createFromString(const estring& str, document_container* container,
+                                              const std::string& master_styles, const std::string& user_styles,
+                                              parse_mode mode);
 
         // Like createFromString, but keeps the parse tree so update_from_string can patch the document.
         static document::ptr createUpdatableFromString(const std::string& html, document_container* container,
                                                        const std::string& master_styles);
+        static document::ptr createUpdatableFromString(const std::string& html, document_container* container,
+                                                       const std::string& master_styles, parse_mode mode);
 
         // Patches an updatable document to the new HTML in place when only inline `style` attribute values
         // and text change and the element structure is the same. Restyles the changed subtrees and rebuilds
