/* -*- Mode: C; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*-
 *
 * Copyright (C) 2026 EmberBSD contributors
 *
 * Origin: EmberBSD UPower backend for the NetBSD envsys(4) framework,
 * AI-assisted.
 *
 * Licensed under the GNU General Public License Version 2
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#ifndef __UP_ENVSYS_NATIVE_H__
#define __UP_ENVSYS_NATIVE_H__

#include <glib.h>
#include <glib-object.h>

G_BEGIN_DECLS

#define UP_TYPE_ENVSYS_NATIVE		(up_envsys_native_get_type ())
#define UP_ENVSYS_NATIVE(o)		(G_TYPE_CHECK_INSTANCE_CAST ((o), UP_TYPE_ENVSYS_NATIVE, UpEnvsysNative))
#define UP_IS_ENVSYS_NATIVE(o)		(G_TYPE_CHECK_INSTANCE_TYPE ((o), UP_TYPE_ENVSYS_NATIVE))

/* One envsys(4) device, for example acpibat0 or acpiacad0. */
typedef struct
{
	GObject	 parent;
	gchar	*device;	/* envsys device name */
	gchar	*path;		/* native path, "/envsys/<device>" */
} UpEnvsysNative;

typedef struct
{
	GObjectClass	parent_class;
} UpEnvsysNativeClass;

GType		 up_envsys_native_get_type	(void);
UpEnvsysNative	*up_envsys_native_new		(const gchar *device);
const gchar	*up_envsys_native_get_device	(UpEnvsysNative *native);
const gchar	*up_envsys_native_get_path	(UpEnvsysNative *native);

G_END_DECLS

#endif /* __UP_ENVSYS_NATIVE_H__ */
