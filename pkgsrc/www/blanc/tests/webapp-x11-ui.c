/* Scoped X11 test helper. BSD-2-Clause. */
#include <sys/types.h>
#include <X11/Xatom.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/XTest.h>
#include <X11/extensions/Xcomposite.h>
#include <X11/keysym.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static Display *display;
static Atom pid_atom;
static unsigned long wanted_pid;
static const char *wanted_class;
static int xerror;

static int
xerror_handler(Display *d, XErrorEvent *event)
{
	(void)d;
	(void)event;
	xerror = 1;
	return 0;
}

static int
sync_ok(void)
{
	XSync(display, False);
	return !xerror;
}

static int
parse_number(const char *text, int base, unsigned long limit, unsigned long *out)
{
	char *end;
	unsigned long value;

	if (*text == '\0' || *text == '-' || *text == '+')
		return 0;
	errno = 0;
	value = strtoul(text, &end, base);
	if (errno != 0 || *end != '\0' || value > limit)
		return 0;
	*out = value;
	return 1;
}

static int
matches(Window window)
{
	Atom actual;
	int format, ok = 0;
	unsigned long count, remaining;
	unsigned char *data = NULL;
	XClassHint hint = { 0 };

	if (XGetWindowProperty(display, window, pid_atom, 0, 1, False,
	    XA_CARDINAL, &actual, &format, &count, &remaining, &data) != Success)
		goto out;
	if (data == NULL || actual != XA_CARDINAL || format != 32 || count != 1 ||
	    *(unsigned long *)data != wanted_pid)
		goto out;
	if (!XGetClassHint(display, window, &hint))
		goto out;
	ok = (hint.res_class != NULL && strcmp(hint.res_class, wanted_class) == 0) ||
	    (hint.res_name != NULL && strcmp(hint.res_name, wanted_class) == 0);
out:
	if (hint.res_name != NULL)
		XFree(hint.res_name);
	if (hint.res_class != NULL)
		XFree(hint.res_class);
	if (data != NULL)
		XFree(data);
	return sync_ok() && ok;
}

static int
window_title(Window window, unsigned char **title, size_t *length)
{
	Atom name, utf8, actual;
	int format;
	unsigned long count, remaining;
	char *legacy = NULL;

	name = XInternAtom(display, "_NET_WM_NAME", False);
	utf8 = XInternAtom(display, "UTF8_STRING", False);
	if (XGetWindowProperty(display, window, name, 0, 128, False,
	    AnyPropertyType, &actual, &format, &count, &remaining, title) != Success ||
	    !sync_ok())
		return 0;
	if (actual == None) {
		if (*title != NULL) {
			XFree(*title);
			*title = NULL;
		}
		if (XFetchName(display, window, &legacy)) {
			*title = (unsigned char *)legacy;
			*length = strnlen(legacy, 512);
		}
		return sync_ok();
	}
	if (actual != utf8 || format != 8 || remaining != 0 || count > 512 ||
	    (count != 0 && *title == NULL))
		return 0;
	*length = count;
	return 1;
}

static int
close_window(Window window)
{
	Atom protocols, delete_window, actual;
	unsigned char *data = NULL;
	unsigned long count, remaining, i;
	int format, found = 0, ok = 0;
	XEvent event = { 0 };

	protocols = XInternAtom(display, "WM_PROTOCOLS", False);
	delete_window = XInternAtom(display, "WM_DELETE_WINDOW", False);
	if (XGetWindowProperty(display, window, protocols, 0, 256, False,
	    XA_ATOM, &actual, &format, &count, &remaining, &data) != Success ||
	    !sync_ok() || actual != XA_ATOM || format != 32 || remaining != 0 ||
	    count > 256 || (count != 0 && data == NULL))
		goto out;
	for (i = 0; i < count; i++)
		if (((Atom *)data)[i] == delete_window)
			found = 1;
	if (!found || !matches(window))
		goto out;
	event.xclient.type = ClientMessage;
	event.xclient.display = display;
	event.xclient.window = window;
	event.xclient.message_type = protocols;
	event.xclient.format = 32;
	event.xclient.data.l[0] = (long)delete_window;
	event.xclient.data.l[1] = CurrentTime;
	ok = XSendEvent(display, window, False, NoEventMask, &event) && sync_ok();
out:
	if (data != NULL)
		XFree(data);
	return ok;
}

static void
walk(Window window, unsigned depth)
{
	Window root, parent, *children = NULL;
	unsigned int n = 0, i;
	XWindowAttributes attrs;
	unsigned char *title = NULL;
	size_t title_length = 0;

	if (depth > 32 || xerror)
		return;
	if (matches(window) && XGetWindowAttributes(display, window, &attrs)) {
		if (!window_title(window, &title, &title_length))
			goto out;
		printf("window=0x%lx pid=%lu mapped=%d width=%d height=%d title_hex=",
		    window, wanted_pid, attrs.map_state == IsViewable,
		    attrs.width, attrs.height);
		if (title != NULL) {
			for (size_t j = 0; j < title_length; j++)
				printf("%02x", title[j]);
		}
		putchar('\n');
	}
	if (XQueryTree(display, window, &root, &parent, &children, &n) && sync_ok())
		for (i = 0; i < n && !xerror; i++)
			walk(children[i], depth + 1);
out:
	if (title != NULL)
		XFree(title);
	if (children != NULL)
		XFree(children);
}

static int
is_ancestor(Window ancestor, Window child)
{
	Window root, parent, *children;
	unsigned int count;
	int i;

	for (i = 0; i < 32 && child != None; i++) {
		if (child == ancestor)
			return 1;
		children = NULL;
		if (!XQueryTree(display, child, &root, &parent, &children, &count) || !sync_ok()) {
			if (children != NULL)
				XFree(children);
			return 0;
		}
		if (children != NULL)
			XFree(children);
		if (child == root || child == parent)
			break;
		child = parent;
	}
	return 0;
}

static int
focus(Window window)
{
	Window focused;
	int revert;

	XRaiseWindow(display, window);
	XSetInputFocus(display, window, RevertToParent, CurrentTime);
	if (!sync_ok())
		return 0;
	XGetInputFocus(display, &focused, &revert);
	return sync_ok() && focused == window;
}

static int
still_focused(Window window)
{
	Window focused;
	int revert;
	XGetInputFocus(display, &focused, &revert);
	return sync_ok() && focused == window && matches(window);
}

static int
send_key(Window window, const char *text)
{
	KeyCode codes[4];
	KeySym symbol;
	unsigned int n = 0, pressed = 0;
	int ok = 0;

	if (strncmp(text, "Ctrl+", 5) == 0) { codes[n++] = XKeysymToKeycode(display, XK_Control_L); text += 5; }
	if (strncmp(text, "Shift+", 6) == 0) { codes[n++] = XKeysymToKeycode(display, XK_Shift_L); text += 6; }
	if (strncmp(text, "Alt+", 4) == 0) { codes[n++] = XKeysymToKeycode(display, XK_Alt_L); text += 4; }
	symbol = XStringToKeysym(text);
	if (symbol == NoSymbol)
		return 0;
	codes[n++] = XKeysymToKeycode(display, symbol);
	for (unsigned int i = 0; i < n; i++)
		if (codes[i] == 0)
			return 0;
	if (!sync_ok() || !focus(window) || !matches(window))
		return 0;
	while (pressed < n) {
		if (!still_focused(window))
			goto release;
		if (!XTestFakeKeyEvent(display, codes[pressed], True, CurrentTime))
			goto release;
		pressed++;
		if (!sync_ok())
			goto release;
	}
	ok = 1;
release:
	/* Release every key whose press was queued, even after an X error. */
	while (pressed > 0)
		if (!XTestFakeKeyEvent(display, codes[--pressed], False, CurrentTime))
			ok = 0;
	XSync(display, False);
	return ok && !xerror;
}

static unsigned char
component(unsigned long pixel, unsigned long mask)
{
	unsigned shift = 0;
	if (mask == 0)
		return 0;
	while ((mask & 1) == 0) { mask >>= 1; shift++; }
	return (unsigned char)(((pixel >> shift) & mask) * 255 / mask);
}

int
main(int argc, char **argv)
{
	XWindowAttributes attrs;
	XImage *image = NULL;
	FILE *out = NULL;
	Window window, root, under, child;
	Pixmap pixmap = None;
	unsigned long id, value;
	int rc = 1, fd = -1, event, error, major, minor, x, y, rx, ry, ax, ay, bx, by;
	unsigned int mask;

	if (argc < 4 || !parse_number(argv[1], 10, INT_MAX, &wanted_pid) || wanted_pid == 0) {
		fprintf(stderr, "usage: x11-ui PID CLASS list | PID CLASS WINDOW focus|key|click|screenshot|close [ARG]\n");
		return 2;
	}
	wanted_class = argv[2];
	display = XOpenDisplay(NULL);
	if (display == NULL)
		goto done;
	XSetErrorHandler(xerror_handler);
	if (!XTestQueryExtension(display, &event, &error, &major, &minor) || !sync_ok())
		goto done;
	pid_atom = XInternAtom(display, "_NET_WM_PID", False);
	if (!sync_ok())
		goto done;
	if (strcmp(argv[3], "list") == 0 && argc == 4) {
		walk(DefaultRootWindow(display), 0);
		rc = xerror ? 1 : 0;
		goto done;
	}
	if (argc < 5 || !parse_number(argv[3], 0, UINT32_MAX, &id) || id == 0)
		goto done;
	window = (Window)id;
	if (!matches(window) || !XGetWindowAttributes(display, window, &attrs) ||
	    !sync_ok() || attrs.map_state != IsViewable)
		goto done;
	if (strcmp(argv[4], "close") == 0 && argc == 5) {
		rc = close_window(window) ? 0 : 1;
	} else if (strcmp(argv[4], "focus") == 0 && argc == 5) {
		rc = focus(window) ? 0 : 1;
	} else if (strcmp(argv[4], "key") == 0 && argc == 6) {
		rc = send_key(window, argv[5]) ? 0 : 1;
	} else if (strcmp(argv[4], "click") == 0 && argc == 7) {
		if (!parse_number(argv[5], 10, INT_MAX, &value)) goto done;
		x = (int)value;
		if (!parse_number(argv[6], 10, INT_MAX, &value)) goto done;
		y = (int)value;
		if (x >= attrs.width || y >= attrs.height || !focus(window) || !matches(window)) goto done;
		if (!XTranslateCoordinates(display, window, DefaultRootWindow(display), x, y, &rx, &ry, &child) || !sync_ok()) goto done;
		if (!XTestFakeMotionEvent(display, DefaultScreen(display), rx, ry, CurrentTime) || !sync_ok()) goto done;
		if (!XQueryPointer(display, DefaultRootWindow(display), &root, &under, &ax, &ay, &bx, &by, &mask) || !sync_ok() || !under || !is_ancestor(under, window) || !still_focused(window)) goto done;
		if (!XTestFakeButtonEvent(display, 1, True, CurrentTime)) goto done;
		/* Always release a queued press, including after an asynchronous error. */
		int pressed_ok = sync_ok();
		int released = XTestFakeButtonEvent(display, 1, False, CurrentTime);
		rc = (pressed_ok && released && sync_ok()) ? 0 : 1;
	} else if (strcmp(argv[4], "screenshot") == 0 && argc == 6) {
		if (attrs.width <= 0 || attrs.height <= 0 || attrs.width > 8192 || attrs.height > 8192) goto done;
		if (!XCompositeQueryExtension(display, &event, &error) || !sync_ok()) goto done;
		major = 0; minor = 2;
		if (!XCompositeQueryVersion(display, &major, &minor) || !sync_ok() ||
		    (major == 0 && minor < 2)) goto done;
		/* Do not redirect windows ourselves; fail if compositor has not done so. */
		pixmap = XCompositeNameWindowPixmap(display, window);
		if (pixmap == None || !sync_ok()) { pixmap = None; goto done; }
		image = XGetImage(display, pixmap, 0, 0, attrs.width, attrs.height, AllPlanes, ZPixmap);
		if (image == NULL || !sync_ok()) goto done;
		fd = open(argv[5], O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW, 0600);
		if (fd < 0 || (out = fdopen(fd, "wb")) == NULL) goto done;
		fd = -1;
		if (fprintf(out, "P6\n%d %d\n255\n", attrs.width, attrs.height) < 0) goto done;
		for (y = 0; y < attrs.height; y++) for (x = 0; x < attrs.width; x++) {
			unsigned long pixel = XGetPixel(image, x, y);
			unsigned char rgb[3] = { component(pixel, attrs.visual->red_mask), component(pixel, attrs.visual->green_mask), component(pixel, attrs.visual->blue_mask) };
			if (fwrite(rgb, 1, sizeof(rgb), out) != sizeof(rgb)) goto done;
		}
		rc = 0;
	}
done:
	if (out != NULL && fclose(out) != 0) rc = 1;
	if (fd >= 0) close(fd);
	if (image != NULL) XDestroyImage(image);
	if (display != NULL && pixmap != None) XFreePixmap(display, pixmap);
	if (display != NULL) XCloseDisplay(display);
	return rc;
}
