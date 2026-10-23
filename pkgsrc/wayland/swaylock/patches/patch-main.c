$NetBSD$

Check allocation results before dereferencing or replacing owned pointers.
Preserve image and event-loop state when allocation fails.
Origin: EmberBSD (AI-assisted); not submitted upstream.

--- main.c.orig
+++ main.c
@@ -5,6 +5,7 @@
 #include <getopt.h>
 #include <poll.h>
 #include <signal.h>
+#include <stdint.h>
 #include <stdbool.h>
 #include <stdio.h>
 #include <stdlib.h>
@@ -266,18 +267,46 @@
 	} else if (strcmp(interface, wl_seat_interface.name) == 0) {
 		struct wl_seat *seat = wl_registry_bind(
 				registry, name, &wl_seat_interface, 4);
+		if (!seat) {
+			swaylock_log(LOG_ERROR, "Unable to bind wl_seat");
+			exit(EXIT_FAILURE);
+		}
 		struct swaylock_seat *swaylock_seat =
 			calloc(1, sizeof(struct swaylock_seat));
+		if (!swaylock_seat) {
+			wl_seat_destroy(seat);
+			swaylock_log_errno(LOG_ERROR, "Unable to allocate wl_seat state");
+			exit(EXIT_FAILURE);
+		}
 		swaylock_seat->state = state;
-		wl_seat_add_listener(seat, &seat_listener, swaylock_seat);
+		if (wl_seat_add_listener(seat, &seat_listener, swaylock_seat) < 0) {
+			wl_seat_destroy(seat);
+			free(swaylock_seat);
+			swaylock_log(LOG_ERROR, "Unable to add wl_seat listener");
+			exit(EXIT_FAILURE);
+		}
 	} else if (strcmp(interface, wl_output_interface.name) == 0) {
 		struct swaylock_surface *surface =
 			calloc(1, sizeof(struct swaylock_surface));
+		if (!surface) {
+			swaylock_log_errno(LOG_ERROR, "Unable to allocate output state");
+			exit(EXIT_FAILURE);
+		}
 		surface->state = state;
 		surface->output = wl_registry_bind(registry, name,
 				&wl_output_interface, 4);
+		if (!surface->output) {
+			free(surface);
+			swaylock_log(LOG_ERROR, "Unable to bind wl_output");
+			exit(EXIT_FAILURE);
+		}
 		surface->output_global_name = name;
-		wl_output_add_listener(surface->output, &_wl_output_listener, surface);
+		if (wl_output_add_listener(surface->output, &_wl_output_listener, surface) < 0) {
+			wl_output_destroy(surface->output);
+			free(surface);
+			swaylock_log(LOG_ERROR, "Unable to add wl_output listener");
+			exit(EXIT_FAILURE);
+		}
 		wl_list_insert(&state->surfaces, &surface->link);
 	} else if (strcmp(interface, ext_session_lock_manager_v1_interface.name) == 0) {
 		state->ext_session_lock_manager_v1 = wl_registry_bind(registry, name,
@@ -323,14 +352,26 @@
 }
 
 static char *join_args(char **argv, int argc) {
-	assert(argc > 0);
-	int len = 0, i;
-	for (i = 0; i < argc; ++i) {
-		len += strlen(argv[i]) + 1;
+	if (argc <= 0) {
+		swaylock_log(LOG_ERROR, "Unable to join an empty image path");
+		return NULL;
+	}
+	size_t len = 0;
+	for (int i = 0; i < argc; ++i) {
+		size_t arg_len = strlen(argv[i]);
+		if (arg_len >= SIZE_MAX - len) {
+			swaylock_log(LOG_ERROR, "Image path is too large");
+			return NULL;
+		}
+		len += arg_len + 1;
 	}
 	char *res = malloc(len);
+	if (!res) {
+		swaylock_log_errno(LOG_ERROR, "Unable to allocate image path");
+		return NULL;
+	}
 	len = 0;
-	for (i = 0; i < argc; ++i) {
+	for (int i = 0; i < argc; ++i) {
 		strcpy(res + len, argv[i]);
 		len += strlen(argv[i]);
 		res[len++] = ' ';
@@ -339,9 +380,25 @@
 	return res;
 }
 
+static void destroy_image(struct swaylock_image *image) {
+	if (!image) {
+		return;
+	}
+	if (image->cairo_surface) {
+		cairo_surface_destroy(image->cairo_surface);
+	}
+	free(image->output_name);
+	free(image->path);
+	free(image);
+}
+
 static void load_image(char *arg, struct swaylock_state *state) {
 	// [[<output>]:]<path>
 	struct swaylock_image *image = calloc(1, sizeof(struct swaylock_image));
+	if (!image) {
+		swaylock_log_errno(LOG_ERROR, "Unable to allocate image state");
+		return;
+	}
 	char *separator = strchr(arg, ':');
 	if (separator) {
 		*separator = '\0';
@@ -351,6 +408,11 @@
 		image->output_name = NULL;
 		image->path = strdup(arg);
 	}
+	if (!image->path || (separator && separator != arg && !image->output_name)) {
+		swaylock_log_errno(LOG_ERROR, "Unable to copy image path");
+		destroy_image(image);
+		return;
+	}
 
 	struct swaylock_image *iter_image, *temp;
 	wl_list_for_each_safe(iter_image, temp, &state->images, link) {
@@ -364,10 +426,7 @@
 						image->path);
 			}
 			wl_list_remove(&iter_image->link);
-			free(iter_image->cairo_surface);
-			free(iter_image->output_name);
-			free(iter_image->path);
-			free(iter_image);
+			destroy_image(iter_image);
 			break;
 		}
 	}
@@ -377,21 +436,32 @@
 	// expansions performed
 	wordexp_t p;
 	while (strstr(image->path, "  ")) {
-		image->path = realloc(image->path, strlen(image->path) + 2);
+		char *path = realloc(image->path, strlen(image->path) + 2);
+		if (!path) {
+			swaylock_log_errno(LOG_ERROR, "Unable to expand image path");
+			destroy_image(image);
+			return;
+		}
+		image->path = path;
 		char *ptr = strstr(image->path, "  ") + 1;
 		memmove(ptr + 1, ptr, strlen(ptr) + 1);
 		*ptr = '\\';
 	}
 	if (wordexp(image->path, &p, 0) == 0) {
-		free(image->path);
-		image->path = join_args(p.we_wordv, p.we_wordc);
+		char *path = join_args(p.we_wordv, p.we_wordc);
 		wordfree(&p);
+		if (!path) {
+			destroy_image(image);
+			return;
+		}
+		free(image->path);
+		image->path = path;
 	}
 
 	// Load the actual image
 	image->cairo_surface = load_background_image(image->path);
 	if (!image->cairo_surface) {
-		free(image);
+		destroy_image(image);
 		return;
 	}
 	wl_list_insert(&state->images, &image->link);
@@ -677,7 +747,13 @@
 		switch (c) {
 		case 'C':
 			if (config_path) {
-				*config_path = strdup(optarg);
+				char *path = strdup(optarg);
+				if (!path) {
+					swaylock_log_errno(LOG_ERROR, "Unable to copy config path");
+					return 1;
+				}
+				free(*config_path);
+				*config_path = path;
 			}
 			break;
 		case 'c':
@@ -1180,6 +1256,11 @@
 		return EXIT_FAILURE;
 	}
 	state.eventloop = loop_create();
+	if (!state.eventloop) {
+		wl_display_disconnect(state.display);
+		free(state.args.font);
+		return EXIT_FAILURE;
+	}
 
 	struct wl_registry *registry = wl_display_get_registry(state.display);
 	wl_registry_add_listener(registry, &registry_listener, &state);
