$NetBSD$

Origin: EmberBSD (AI-assisted).
Bound the real RGB parser and terminate only successful, bounded reads.
Keep rejected and empty device data on the normal cleanup path.
Use -1 as the unused descriptor sentinel and release descriptor zero.

--- programs/sxmo_status_led.c.orig
+++ programs/sxmo_status_led.c
@@ -51,8 +51,9 @@
 };
 
 void close_single_led(struct led_handle *led) {
-	if (led->brightness > 0)
+	if (led->brightness >= 0)
 		close(led->brightness);
+	led->brightness = -1;
 }
 
 struct multicolor_handle {
@@ -123,24 +124,28 @@
 	int color_index = 0;
 	int start = 0;
 	int i = 0;
-	memset(colors, COLOR_MAX, sizeof(enum color)*3);
+	for (int color = 0; color < COLOR_MAX; color++) {
+		colors[color] = COLOR_MAX;
+	}
 
 	while (i < length) {
 		// skip whitespace
-		while (i < length && isspace(input[i])) { i++; }
+		while (i < length && isspace((unsigned char)input[i])) { i++; }
 		start = i;
 
 		// find the end of the word (next whitespace)
-		while (i < length && !isspace(input[i])) { i++; }
+		while (i < length && !isspace((unsigned char)input[i])) { i++; }
 
 		if (i == start) break;
 
+		if (color_index == COLOR_MAX) return false;
+
 		// now start points to the first char in the word and i is the last
-		if (strncmp(&input[start], "red", i-start) == 0) {
+		if (i-start == 3 && strncmp(&input[start], "red", i-start) == 0) {
 			colors[color_index] = COLOR_RED;
-		} else if (strncmp(&input[start], "green", i-start) == 0) {
+		} else if (i-start == 5 && strncmp(&input[start], "green", i-start) == 0) {
 			colors[color_index] = COLOR_GREEN;
-		} else if (strncmp(&input[start], "blue", i-start) == 0) {
+		} else if (i-start == 4 && strncmp(&input[start], "blue", i-start) == 0) {
 			colors[color_index] = COLOR_BLUE;
 		} else {
 			info("Unknown color: \"%.*s\"\n", i-start, &input[start]);
@@ -155,12 +160,12 @@
 	// them to what we expected to have. The color enum starts at zero and
 	// increments by 1, so we can bitshift by that number to decide what bit
 	// to use.
-	return (BIT(colors[0]) | BIT(colors[1]) | BIT(colors[2]))
+	return color_index == COLOR_MAX && (BIT(colors[0]) | BIT(colors[1]) | BIT(colors[2]))
 		== (BIT(COLOR_RED) | BIT(COLOR_BLUE) | BIT(COLOR_GREEN));
 }
 
 bool open_multicolor_led(char *type, struct multicolor_handle *dst) {
-	int ret, fd = 0;
+	int ret, fd = -1;
 	char buf[128];
 
 	memset(dst, 0, sizeof(*dst));
@@ -172,14 +177,15 @@
 		goto error;
 	}
 
-	int size = read(fd, buf, sizeof(buf));
+	int size = read(fd, buf, sizeof(buf) - 1);
+	if (size <= 0) {
+		error("Failed to read multi_index");
+		goto error;
+	}
+	close(fd);
+	fd = -1;
+
 	buf[size] = 0;
-	if (size <= 0) {
-		perror("while reading multi_index");
-		exit(1);
-	}
-	close(fd);
-
 	if (!parse_color_ids(buf, size, dst->color_ids)) {
 		info("failed to parse multi_index\n");
 		goto error;
@@ -187,7 +193,7 @@
 
 	snprintf(buf, sizeof(buf), "%s/rgb:%s/max_brightness", led_dir, type);
 	fd = open(buf, O_RDONLY);
-	if (fd <= 0)
+	if (fd < 0)
 		goto error;
 
 	ret = dreadint(fd, &dst->max_brightness);
@@ -196,6 +202,7 @@
 		goto error;
 	}
 	close(fd);
+	fd = -1;
 
 	snprintf(buf, sizeof(buf), "%s/rgb:%s/brightness", led_dir, type);
 	dst->brightness = fopen(buf, "r+");
@@ -210,7 +217,7 @@
 	return true;
 
 error:
-	if (fd > 0) close(fd);
+	if (fd >= 0) close(fd);
 	if (dst->brightness) fclose(dst->brightness);
 	if (dst->multi_intensity) fclose(dst->multi_intensity);
 
@@ -235,7 +242,7 @@
 
 	snprintf(buf, sizeof(buf), "%s/%s:%s/max_brightness", led_dir, color, type);
 	fd = open(buf, O_RDONLY);
-	if (fd <= 0)
+	if (fd < 0)
 		return fd;
 
 	ret = dreadint(fd, &led->max_brightness);
@@ -253,6 +260,7 @@
 ) {
 	struct led_handle *ret = led->group;
 	memset(ret, 0, sizeof(struct led_handle) * 3);
+	for (int color = 0; color < COLOR_MAX; color++) ret[color].brightness = -1;
 
 	if (-1 == open_monocolor_led(red, type, flip, &ret[COLOR_RED]))
 		goto error;
