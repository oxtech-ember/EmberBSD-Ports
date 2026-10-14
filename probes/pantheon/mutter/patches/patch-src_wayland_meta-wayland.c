$NetBSD$

The linux-drm-syncobj staging protocol needs the Linux DRM syncobj UAPI
and native backend headers; keep the whole integration Linux-only.
Origin: EmberBSD (AI-assisted).

--- src/wayland/meta-wayland.c	2026-09-15 17:26:39.000000000 +0300
+++ src/wayland/meta-wayland.c	2026-10-14 11:51:39.464707907 +0300
@@ -54,7 +54,19 @@
 #include "wayland/meta-wayland-inhibit-shortcuts-dialog.h"
 #include "wayland/meta-wayland-inhibit-shortcuts.h"
 #include "wayland/meta-wayland-legacy-xdg-foreign.h"
+#ifdef __linux__
 #include "wayland/meta-wayland-linux-drm-syncobj.h"
+#endif
+#ifndef __linux__
+gboolean
+meta_wayland_surface_explicit_sync_validate (MetaWaylandSurface      *surface,
+                                             MetaWaylandSurfaceState *state)
+{
+  /* Explicit synchronization needs the linux-drm-syncobj protocol,
+   * which is Linux-only; nothing to validate without it. */
+  return TRUE;
+}
+#endif
 #include "wayland/meta-wayland-outputs.h"
 #include "wayland/meta-wayland-presentation-time-private.h"
 #include "wayland/meta-wayland-private.h"
@@ -1027,7 +1039,9 @@
   meta_wayland_activation_init (compositor);
   meta_wayland_transaction_init (compositor);
   meta_wayland_idle_inhibit_init (compositor);
+#ifdef __linux__
   meta_wayland_drm_syncobj_init (compositor);
+#endif
   meta_wayland_init_xdg_wm_dialog (compositor);
   meta_wayland_init_color_management (compositor);
   meta_wayland_xdg_session_management_init (compositor);
--- src/wayland/meta-wayland-surface-private.h	2026-09-15 17:26:39.000000000 +0300
+++ src/wayland/meta-wayland-surface-private.h	2026-10-14 11:46:53.369282229 +0300
@@ -30,7 +30,9 @@
 #include "meta/meta-wayland-surface.h"
 #include "wayland/meta-wayland-pointer-constraints.h"
 #include "wayland/meta-wayland-types.h"
+#ifdef __linux__
 #include "wayland/meta-wayland-linux-drm-syncobj.h"
+#endif
 
 #define META_TYPE_WAYLAND_SURFACE_ROLE (meta_wayland_surface_role_get_type ())
 G_DECLARE_DERIVABLE_TYPE (MetaWaylandSurfaceRole, meta_wayland_surface_role,
@@ -132,11 +134,13 @@
   MetaWaylandXdgPositioner *xdg_positioner;
   uint32_t xdg_popup_reposition_token;
 
+#ifdef __linux__
   /* Explicit Synchronization */
   struct {
     MetaWaylandSyncPoint *acquire;
     MetaWaylandSyncPoint *release;
   } drm_syncobj;
+#endif
 
   gboolean has_new_color_state;
   ClutterColorState *color_state;
--- src/wayland/meta-wayland-surface.c	2026-09-15 17:26:39.000000000 +0300
+++ src/wayland/meta-wayland-surface.c	2026-10-14 11:51:39.465851326 +0300
@@ -51,11 +51,23 @@
 #include "wayland/meta-wayland-viewporter.h"
 #include "wayland/meta-wayland-xdg-shell.h"
 #include "wayland/meta-window-wayland.h"
+#ifdef __linux__
 #include "wayland/meta-wayland-linux-drm-syncobj.h"
-
+#endif
 #ifdef HAVE_XWAYLAND
 #include "wayland/meta-window-xwayland.h"
 #include "wayland/meta-xwayland-private.h"
+
+#ifndef __linux__
+static gboolean
+meta_wayland_surface_explicit_sync_validate (MetaWaylandSurface      *surface,
+                                             MetaWaylandSurfaceState *state)
+{
+  /* Explicit synchronization needs the linux-drm-syncobj protocol,
+   * which is Linux-only; nothing to validate without it. */
+  return TRUE;
+}
+#endif
 #endif
 
 enum
@@ -459,8 +471,10 @@
 
   state->xdg_popup_reposition_token = 0;
 
+#ifdef __linux__
   state->drm_syncobj.acquire = NULL;
   state->drm_syncobj.release = NULL;
+#endif
 
   state->has_new_color_state = FALSE;
   state->color_state = NULL;
@@ -487,8 +501,10 @@
   MetaWaylandFrameCallback *cb, *next;
 
   g_clear_object (&state->texture);
+#ifdef __linux__
   g_clear_object (&state->drm_syncobj.acquire);
   g_clear_object (&state->drm_syncobj.release);
+#endif
   g_clear_object (&state->color_state);
 
   g_clear_pointer (&state->surface_damage, mtk_region_unref);
@@ -673,10 +689,12 @@
       to->xdg_popup_reposition_token = from->xdg_popup_reposition_token;
     }
 
+#ifdef __linux__
   g_set_object (&to->drm_syncobj.acquire, from->drm_syncobj.acquire);
   g_clear_object (&from->drm_syncobj.acquire);
   g_set_object (&to->drm_syncobj.release, from->drm_syncobj.release);
   g_clear_object (&from->drm_syncobj.release);
+#endif
 
   if (from->has_new_color_state)
     {
@@ -1117,7 +1135,9 @@
   MetaWaylandBuffer *buffer = pending->buffer;
   MetaWaylandTransaction *transaction;
   MetaWaylandSurface *subsurface_surface;
+#ifdef __linux__
   MetaWaylandSyncPoint *release_point = pending->drm_syncobj.release;
+#endif
 
   COGL_TRACE_BEGIN_SCOPED (MetaWaylandSurfaceCommit,
                            "Meta::WaylandSurface::commit()");
@@ -1155,8 +1175,10 @@
 
       pending->texture = g_object_ref (surface->committed_state.texture);
 
+#ifdef __linux__
       if (release_point)
         g_ptr_array_add (buffer->release_points, g_object_ref (release_point));
+#endif
 
       meta_wayland_buffer_inc_use_count (buffer);
     }
--- src/wayland/meta-wayland-buffer.c	2026-09-15 17:26:39.000000000 +0300
+++ src/wayland/meta-wayland-buffer.c	2026-10-14 11:46:53.373588901 +0300
@@ -60,7 +60,9 @@
 #include "common/meta-drm-format-helpers.h"
 #include "common/meta-drm-timeline.h"
 #include "compositor/meta-multi-texture-format-private.h"
+#ifdef __linux__
 #include "wayland/meta-wayland-linux-drm-syncobj.h"
+#endif
 
 #ifdef HAVE_NATIVE_BACKEND
 #include "backends/native/meta-drm-buffer-gbm.h"
@@ -712,6 +714,7 @@
   buffer->use_count++;
 }
 
+#ifdef __linux__
 static void
 handle_release_points (MetaWaylandBuffer *buffer)
 {
@@ -748,6 +751,7 @@
   g_ptr_array_remove_range (buffer->release_points, 0,
                             buffer->release_points->len);
 }
+#endif
 
 void
 meta_wayland_buffer_dec_use_count (MetaWaylandBuffer *buffer)
@@ -761,8 +765,10 @@
       if (buffer->resource)
         wl_buffer_send_release (buffer->resource);
 
+#ifdef __linux__
       if (buffer->release_points->len)
         handle_release_points (buffer);
+#endif
     }
 }
 
--- src/wayland/meta-wayland-transaction.c	2026-09-15 17:26:39.000000000 +0300
+++ src/wayland/meta-wayland-transaction.c	2026-10-14 11:46:53.374637277 +0300
@@ -26,7 +26,9 @@
 #include "wayland/meta-wayland.h"
 #include "wayland/meta-wayland-buffer.h"
 #include "wayland/meta-wayland-dma-buf.h"
+#ifdef __linux__
 #include "wayland/meta-wayland-linux-drm-syncobj.h"
+#endif
 
 #define META_WAYLAND_TRANSACTION_NONE ((void *)(uintptr_t) G_MAXSIZE)
 
@@ -396,6 +398,7 @@
   return TRUE;
 }
 
+#ifdef __linux__
 static gboolean
 meta_wayland_transaction_add_drm_syncobj_source (MetaWaylandTransaction *transaction,
                                                  MetaWaylandBuffer      *buffer,
@@ -423,6 +426,7 @@
 
   return TRUE;
 }
+#endif
 
 static void
 meta_wayland_transaction_add_placement_surfaces (MetaWaylandTransaction  *transaction,
@@ -464,10 +468,13 @@
         {
           MetaWaylandBuffer *buffer = entry->state->buffer;
 
-          if ((entry->state->drm_syncobj.acquire &&
+          if (
+#ifdef __linux__
+              (entry->state->drm_syncobj.acquire &&
                meta_wayland_transaction_add_drm_syncobj_source (transaction, buffer,
-                                                                entry->state->drm_syncobj.acquire))
-              || (buffer &&
+                                                                entry->state->drm_syncobj.acquire)) ||
+#endif
+              (buffer &&
                   meta_wayland_transaction_add_dma_buf_source (transaction, buffer)))
             maybe_apply = FALSE;
 
