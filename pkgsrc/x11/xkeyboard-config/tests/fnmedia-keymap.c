/* SPDX-License-Identifier: MIT */
/*
 * Compile the evdev keymap of an XKB tree with each fnmedia option and
 * check the keysyms of the function row.  Usage: fnmedia-keymap XKB_ROOT,
 * where XKB_ROOT is the installed tree (DESTDIR/PREFIX/share/
 * xkeyboard-config-2) with rules/evdev, symbols/fnmedia and types/fnmedia.
 * Build: cc -std=c11 -o fnmedia-keymap fnmedia-keymap.c -lxkbcommon
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <xkbcommon/xkbcommon.h>

#define EV(code)	((code) + 8)	/* evdev code to XKB keycode */

enum mods { NONE = 0, SHIFT = 1, CTRL = 2, ALT = 4, SUPER = 8 };

struct check {
	const char *option;
	unsigned int key;	/* evdev code */
	unsigned int mods;
	const char *keysym;
};

static const struct check checks[] = {
	/* MSI Vector: the printed action without Fn. */
	{ "fnmedia:msi_vector", 59, NONE, "XF86AudioMute" },	/* F1 */
	{ "fnmedia:msi_vector", 60, SHIFT, "XF86AudioLowerVolume" },
	{ "fnmedia:msi_vector", 61, NONE, "XF86AudioRaiseVolume" },
	{ "fnmedia:msi_vector", 62, NONE, "XF86TouchpadToggle" },
	{ "fnmedia:msi_vector", 63, NONE, "XF86AudioMicMute" },
	{ "fnmedia:msi_vector", 64, NONE, "XF86Bluetooth" },
	{ "fnmedia:msi_vector", 65, NONE, "XF86Tools" },
	{ "fnmedia:msi_vector", 66, NONE, "XF86KbdLightOnOff" },
	{ "fnmedia:msi_vector", 67, NONE, "XF86MonBrightnessDown" },
	{ "fnmedia:msi_vector", 68, NONE, "XF86MonBrightnessUp" },
	{ "fnmedia:msi_vector", 87, NONE, "XF86Display" },	/* F11 */
	{ "fnmedia:msi_vector", 88, NONE, "F12" },
	/* F-keys with Control, Alt or Super; consoles with Control+Alt. */
	{ "fnmedia:msi_vector", 62, ALT, "F4" },
	{ "fnmedia:msi_vector", 62, CTRL, "F4" },
	{ "fnmedia:msi_vector", 59, SUPER, "F1" },
	{ "fnmedia:msi_vector", 60, CTRL | ALT, "XF86Switch_VT_2" },
	/* Fn with the key gives the F-key. */
	{ "fnmedia:msi_vector", 113, NONE, "F1" },	/* KEY_MUTE */
	{ "fnmedia:msi_vector", 114, NONE, "F2" },	/* KEY_VOLUMEDOWN */
	{ "fnmedia:msi_vector", 115, NONE, "F3" },	/* KEY_VOLUMEUP */
	{ "fnmedia:msi_vector", 190, NONE, "F5" },	/* KEY_F20 */
	{ "fnmedia:msi_vector", 237, NONE, "F6" },	/* KEY_BLUETOOTH */
	{ "fnmedia:msi_vector", 171, NONE, "F7" },	/* KEY_CONFIG */
	/* Fn+F4: Control+Super+F24 stays the touchpad toggle. */
	{ "fnmedia:msi_vector", 194, CTRL | SUPER, "XF86TouchpadToggle" },

	/* QBOOK15. */
	{ "fnmedia:qbook15", 59, NONE, "F1" },
	{ "fnmedia:qbook15", 60, NONE, "XF86AudioMute" },
	{ "fnmedia:qbook15", 61, SHIFT, "XF86AudioLowerVolume" },
	{ "fnmedia:qbook15", 62, NONE, "XF86AudioRaiseVolume" },
	{ "fnmedia:qbook15", 64, NONE, "XF86MonBrightnessDown" },
	{ "fnmedia:qbook15", 65, NONE, "XF86MonBrightnessUp" },
	{ "fnmedia:qbook15", 66, NONE, "XF86AudioPrev" },
	{ "fnmedia:qbook15", 67, NONE, "XF86AudioNext" },
	{ "fnmedia:qbook15", 62, ALT, "F4" },
	{ "fnmedia:qbook15", 61, CTRL | ALT, "XF86Switch_VT_3" },
	{ "fnmedia:qbook15", 113, NONE, "F2" },
	{ "fnmedia:qbook15", 115, NONE, "F4" },
	{ "fnmedia:qbook15", 165, NONE, "F8" },		/* KEY_PREVIOUSSONG */
	{ "fnmedia:qbook15", 163, NONE, "F9" },		/* KEY_NEXTSONG */

	/* Without an option the row is unchanged. */
	{ "", 59, NONE, "F1" },
	{ "", 113, NONE, "XF86AudioMute" },
};

static struct xkb_keymap *
keymap_for(struct xkb_context *ctx, const char *option)
{
	struct xkb_rule_names names = {
		.rules = "evdev",
		.model = "pc105",
		.layout = "us",
		.variant = "",
		.options = option,
	};

	return xkb_keymap_new_from_names(ctx, &names,
	    XKB_KEYMAP_COMPILE_NO_FLAGS);
}

static xkb_mod_mask_t
mask_for(struct xkb_keymap *keymap, unsigned int mods)
{
	static const struct { unsigned int bit; const char *name; } names[] = {
		{ SHIFT, XKB_MOD_NAME_SHIFT },
		{ CTRL, XKB_MOD_NAME_CTRL },
		{ ALT, XKB_MOD_NAME_ALT },
		{ SUPER, XKB_MOD_NAME_LOGO },
	};
	xkb_mod_mask_t mask = 0;
	size_t i;

	for (i = 0; i < sizeof(names) / sizeof(*names); i++) {
		if (mods & names[i].bit) {
			xkb_mod_index_t idx =
			    xkb_keymap_mod_get_index(keymap, names[i].name);

			if (idx == XKB_MOD_INVALID)
				return 0;
			mask |= (xkb_mod_mask_t)1 << idx;
		}
	}
	return mask;
}

int
main(int argc, char **argv)
{
	struct xkb_context *ctx;
	const char *current = NULL;
	struct xkb_keymap *keymap = NULL;
	size_t i;
	int failed = 0;

	if (argc != 2) {
		fprintf(stderr, "usage: %s XKB_ROOT\n", argv[0]);
		return 2;
	}
	ctx = xkb_context_new(XKB_CONTEXT_NO_DEFAULT_INCLUDES |
	    XKB_CONTEXT_NO_ENVIRONMENT_NAMES);
	if (ctx == NULL || !xkb_context_include_path_append(ctx, argv[1])) {
		fprintf(stderr, "cannot use XKB root %s\n", argv[1]);
		return 2;
	}
	for (i = 0; i < sizeof(checks) / sizeof(*checks); i++) {
		const struct check *c = &checks[i];
		struct xkb_state *state;
		xkb_mod_mask_t mask;
		xkb_keysym_t sym;
		char name[64];

		if (current == NULL || strcmp(current, c->option) != 0) {
			xkb_keymap_unref(keymap);
			keymap = keymap_for(ctx, c->option);
			current = c->option;
			if (keymap == NULL) {
				fprintf(stderr, "option '%s': no keymap\n",
				    c->option);
				return 1;
			}
		}
		mask = mask_for(keymap, c->mods);
		if (c->mods != NONE && mask == 0) {
			fprintf(stderr, "option '%s': no modifiers\n",
			    c->option);
			return 1;
		}
		state = xkb_state_new(keymap);
		xkb_state_update_mask(state, mask, 0, 0, 0, 0, 0);
		sym = xkb_state_key_get_one_sym(state, EV(c->key));
		xkb_keysym_get_name(sym, name, sizeof(name));
		if (strcmp(name, c->keysym) != 0) {
			fprintf(stderr, "option '%s' key %u mods %u: %s, "
			    "expected %s\n", c->option, c->key, c->mods,
			    name, c->keysym);
			failed = 1;
		}
		xkb_state_unref(state);
	}
	xkb_keymap_unref(keymap);
	xkb_context_unref(ctx);
	if (!failed)
		printf("fnmedia keymap: %zu checks ok\n", i);
	return failed;
}
