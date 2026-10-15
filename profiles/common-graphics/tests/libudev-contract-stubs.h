/* SPDX-License-Identifier: BSD-2-Clause */
/* These unrelated hardware/property paths must never run in this test. */
#define UNUSED_HANDLER(name) \
void name(struct udev_device *device) { (void)device; abort(); }
UNUSED_HANDLER(create_keyboard_handler)
UNUSED_HANDLER(create_mouse_handler)
UNUSED_HANDLER(create_joystick_handler)
UNUSED_HANDLER(create_touchpad_handler)
UNUSED_HANDLER(create_touchscreen_handler)
UNUSED_HANDLER(create_sysmouse_handler)
UNUSED_HANDLER(create_kbdmux_handler)
UNUSED_HANDLER(create_drm_handler)
UNUSED_HANDLER(create_net_handler)

const char *
_udev_device_get_syspath(struct udev_device *device)
{
	(void)device;
	abort();
}

struct udev_device *
udev_device_new_common(struct udev *context, const char *path, int action)
{
	(void)context;
	(void)path;
	(void)action;
	abort();
}

struct udev_device *
udev_device_unref(struct udev_device *device)
{
	(void)device;
	abort();
}

#define UNUSED_LIST(name) \
struct udev_list *name(struct udev_device *device) { (void)device; abort(); }
UNUSED_LIST(udev_device_get_properties_list)
UNUSED_LIST(udev_device_get_sysattr_list)
UNUSED_LIST(udev_device_get_tags_list)
