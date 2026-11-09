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

#include "up-envsys-native.h"
#include "up-native.h"

G_DEFINE_TYPE (UpEnvsysNative, up_envsys_native, G_TYPE_OBJECT)

static void
up_envsys_native_finalize (GObject *object)
{
	UpEnvsysNative *native = UP_ENVSYS_NATIVE (object);

	g_free (native->device);
	g_free (native->path);

	G_OBJECT_CLASS (up_envsys_native_parent_class)->finalize (object);
}

static void
up_envsys_native_class_init (UpEnvsysNativeClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS (klass);

	object_class->finalize = up_envsys_native_finalize;
}

static void
up_envsys_native_init (UpEnvsysNative *self)
{
}

UpEnvsysNative *
up_envsys_native_new (const gchar *device)
{
	UpEnvsysNative *native;

	native = UP_ENVSYS_NATIVE (g_object_new (UP_TYPE_ENVSYS_NATIVE, NULL));
	native->device = g_strdup (device);
	native->path = g_strdup_printf ("/envsys/%s", device);
	return native;
}

const gchar *
up_envsys_native_get_device (UpEnvsysNative *native)
{
	return native->device;
}

const gchar *
up_envsys_native_get_path (UpEnvsysNative *native)
{
	return native->path;
}

/**
 * up_native_get_native_path:
 * @object: the native tracking object
 *
 * Return value: the unique native path of the device, e.g. "/envsys/acpibat0"
 **/
const gchar *
up_native_get_native_path (GObject *object)
{
	return up_envsys_native_get_path (UP_ENVSYS_NATIVE (object));
}
