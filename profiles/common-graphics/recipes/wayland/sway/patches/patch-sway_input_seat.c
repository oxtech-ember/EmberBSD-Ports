$NetBSD$

Destroy seats before configuration loading has completed. The default seat
already exists when IPC startup can fail. Only update a handler context when
the configuration exists; keep the remaining resource cleanup unchanged.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- sway/input/seat.c.orig
+++ sway/input/seat.c
@@ -73,7 +73,7 @@
 static void handle_seat_destroy(struct wl_listener *listener, void *data) {
 	struct sway_seat *seat = wl_container_of(listener, seat, destroy);
 
-	if (seat == config->handler_context.seat) {
+	if (config && seat == config->handler_context.seat) {
 		config->handler_context.seat = input_manager_get_default_seat();
 	}
 	struct sway_seat_device *seat_device, *next;
