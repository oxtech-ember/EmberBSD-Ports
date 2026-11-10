$NetBSD$

Call get_popup when std::any_cast misses xdg_popup* across Qt DSOs.
Qt 6.12 and layer-shell-qt 6.8.2 can disagree on type_info, so any_cast
returns empty and plasmashell popup has no parent; KWin then kills the
client ("Cannot attach popup of unknown type" / xdg_wm_base error 3).
Fall back to the held wl_proxy and require interface name xdg_popup.
Origin: EmberBSD (AI-assisted).

--- src/qwaylandlayersurface.cpp.orig
+++ src/qwaylandlayersurface.cpp
@@ -17,6 +17,8 @@
 
 #include <QGuiApplication>
 
+#include <cstring>
+
 namespace LayerShellQt
 {
 QWaylandLayerSurface::QWaylandLayerSurface(QWaylandLayerShellIntegration *shell, QtWaylandClient::QWaylandWindow *window)
@@ -123,6 +125,28 @@
 
     if (auto role = std::any_cast<::xdg_popup *>(&anyRole)) {
         get_popup(*role);
+        return;
+    }
+
+    // Qt and this library can own different type_info for ::xdg_popup*.
+    // any_cast then fails even when the held value is a valid xdg_popup*.
+    // Recover the pointer from std::any's small-object slot and confirm the
+    // Wayland interface name before calling get_popup (EmberBSD).
+    ::xdg_popup *fallback = nullptr;
+    if (anyRole.has_value()) {
+        void *held = nullptr;
+        std::memcpy(&held, reinterpret_cast<const char *>(&anyRole) + sizeof(void *), sizeof(held));
+        auto *proxy = static_cast<struct wl_proxy *>(held);
+        if (proxy) {
+            const char *iface = wl_proxy_get_class(proxy);
+            if (iface && std::strcmp(iface, "xdg_popup") == 0) {
+                fallback = reinterpret_cast<::xdg_popup *>(proxy);
+            }
+        }
+    }
+
+    if (fallback) {
+        get_popup(fallback);
     } else {
         qCWarning(LAYERSHELLQT) << "Cannot attach popup of unknown type";
     }
