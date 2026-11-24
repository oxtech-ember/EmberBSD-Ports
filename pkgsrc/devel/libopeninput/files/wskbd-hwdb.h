/*	$NetBSD$	*/
/* SPDX-License-Identifier: MIT */

/*
 * Keyboard scan code mappings from systemd hwdb files.
 *
 * Linux applies the KEYBOARD_KEY_<scan code>=<key> properties of the
 * hwdb records that match a keyboard.  This module reads the *.hwdb files
 * of one directory and applies the records of PC (AT) keyboards to a scan
 * code map of the wscons XT translation.
 */

#ifndef _LIBINPUT_WSKBD_HWDB_H
#define _LIBINPUT_WSKBD_HWDB_H

#include <stddef.h>
#include <stdint.h>

/*
 * DMI strings of the system in the format of Linux.  bd has the format
 * MM/DD/YYYY.  A NULL field is not known.
 */
struct wskbd_hwdb_dmi {
	const char *bvn;	/* BIOS vendor */
	const char *bvr;	/* BIOS version */
	const char *bd;		/* BIOS date */
	const char *svn;	/* system vendor */
	const char *pn;		/* system product */
	const char *pvr;	/* system version */
	const char *rvn;	/* board vendor */
	const char *rn;		/* board name */
	const char *rvr;	/* board version */
	const char *cvn;	/* chassis vendor */
	const char *cvr;	/* chassis version */
};

/*
 * Write the DMI modalias of DMI ("dmi:bvn...:") to BUF, as Linux does:
 * each field without the characters that are not printable, spaces and
 * colons.  Linux leaves out a field that the firmware does not give; here
 * an unknown field is empty, because the hwdb patterns name the fields
 * ("dmi:bvn*:bvr*:bd*:svn...") and the system can know fewer fields than
 * Linux.  Return 0, or -1 when BUF is too small.
 */
int wskbd_hwdb_modalias(const struct wskbd_hwdb_dmi *dmi, char *buf,
    size_t size);

/*
 * Return the evdev code of the hwdb key name NAME ("mute", "btn_left"),
 * or -1 for an unknown name.
 */
int wskbd_hwdb_key(const char *name);

/*
 * Apply to MAP (SIZE scan codes) the KEYBOARD_KEY_ properties of the PC
 * keyboard records in the *.hwdb files of DIR that match MODALIAS.  The
 * files are read in name order; a later property replaces an earlier one.
 * Return the number of properties applied.
 */
size_t wskbd_hwdb_apply(const char *dir, const char *modalias, uint32_t *map,
    size_t size);

#endif
