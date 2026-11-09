/* -*- Mode: C; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*-
 *
 * Copyright (C) 2026 EmberBSD contributors
 *
 * Origin: EmberBSD UPower backend for the NetBSD envsys(4) framework.
 * The structure follows the OpenBSD and FreeBSD backends. AI-assisted.
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

/*
 * Data source: the envsys(4) dictionary from /dev/sysmon. The driver
 * acpibat(4) exports one array of sensors for each battery and
 * acpiacad(4) exports one "connected" indicator for each AC adapter.
 * powerd(8) holds /dev/power exclusively, so this backend polls.
 */

#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/envsys.h>
#include <prop/proplib.h>

#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>

#include "up-envsys-native.h"
#include "up-backend.h"
#include "up-daemon.h"
#include "up-device.h"
#include "up-config.h"
#include "up-backend-bsd-private.h"

#define UP_SYSMON_DEVICE		"/dev/sysmon"
#define UP_BACKEND_REFRESH_TIMEOUT	30	/* seconds */
#define UP_BACKEND_MAX_TIME		(20 * 60 * 60)	/* seconds */

static void	up_backend_class_init	(UpBackendClass	*klass);
static void	up_backend_init	(UpBackend		*backend);
static void	up_backend_finalize	(GObject		*object);

static gboolean	up_envsys_device_get_on_battery	(UpDevice *device, gboolean *on_battery);
static gboolean	up_envsys_device_get_online	(UpDevice *device, gboolean *online);
static gboolean	up_envsys_device_refresh	(UpDevice *device, UpRefreshReason reason);

struct UpBackendPrivate
{
	UpDaemon		*daemon;
	GPtrArray		*devices;
	UpConfig		*config;
	GDBusProxy		*seat_manager_proxy;
};

enum {
	SIGNAL_DEVICE_ADDED,
	SIGNAL_DEVICE_REMOVED,
	SIGNAL_LAST
};

static guint signals [SIGNAL_LAST] = { 0 };

G_DEFINE_TYPE_WITH_PRIVATE (UpBackend, up_backend, G_TYPE_OBJECT)

/* One battery sample decoded from the envsys sensor array. */
typedef struct {
	gboolean	present;
	gboolean	charging;
	gboolean	discharging;	/* acpibat reports a discharge rate */
	gboolean	amp_hours;	/* capacities in Ah, rates in A */
	gint		charge_state;	/* ENVSYS_BATTERY_CAPACITY_* or 0 */
	gdouble		design_voltage;	/* V */
	gdouble		voltage;	/* V */
	gdouble		design_cap;	/* Wh or Ah */
	gdouble		last_full_cap;	/* Wh or Ah */
	gdouble		charge;		/* Wh or Ah */
	gdouble		rate;		/* W or A, > 0 when valid */
} UpEnvsysBattery;

/**
 * up_backend_envsys_fetch:
 *
 * Reads the whole envsys dictionary. Returns NULL on error.
 **/
static prop_dictionary_t
up_backend_envsys_fetch (void)
{
	prop_dictionary_t dict = NULL;
	int fd, error;

	fd = open (UP_SYSMON_DEVICE, O_RDONLY);
	if (fd < 0) {
		g_warning ("unable to open %s: %s", UP_SYSMON_DEVICE, g_strerror (errno));
		return NULL;
	}
	error = prop_dictionary_recv_ioctl (fd, ENVSYS_GETDICTIONARY, &dict);
	close (fd);
	if (error != 0) {
		g_warning ("ENVSYS_GETDICTIONARY failed: %s", g_strerror (error));
		return NULL;
	}
	return dict;
}

/**
 * up_backend_envsys_device_class:
 *
 * Returns the "device-class" string of one envsys device array, or NULL.
 * The returned string belongs to the dictionary.
 **/
static const char *
up_backend_envsys_device_class (prop_array_t array)
{
	prop_object_iterator_t iter;
	prop_object_t obj;
	prop_dictionary_t props;
	const char *class_name = NULL;

	iter = prop_array_iterator (array);
	if (iter == NULL)
		return NULL;
	while ((obj = prop_object_iterator_next (iter)) != NULL) {
		if (prop_object_type (obj) != PROP_TYPE_DICTIONARY)
			continue;
		props = prop_dictionary_get (obj, "device-properties");
		if (props == NULL)
			continue;
		prop_dictionary_get_string (props, "device-class", &class_name);
		break;
	}
	prop_object_iterator_release (iter);
	return class_name;
}

/**
 * up_backend_envsys_sensor:
 *
 * Finds the sensor dictionary with the given description.
 **/
static prop_dictionary_t
up_backend_envsys_sensor (prop_array_t array, const char *description)
{
	prop_object_iterator_t iter;
	prop_object_t obj;
	prop_dictionary_t found = NULL;
	const char *desc;

	iter = prop_array_iterator (array);
	if (iter == NULL)
		return NULL;
	while ((obj = prop_object_iterator_next (iter)) != NULL) {
		if (prop_object_type (obj) != PROP_TYPE_DICTIONARY)
			continue;
		if (!prop_dictionary_get_string (obj, "description", &desc))
			continue;
		if (strcmp (desc, description) == 0) {
			found = obj;
			break;
		}
	}
	prop_object_iterator_release (iter);
	return found;
}

/**
 * up_backend_envsys_sensor_usable:
 *
 * Returns TRUE when the sensor exists and its state carries a value.
 * The states "valid", "warning-*" and "critical*" carry a value;
 * "invalid" and "unknown" do not.
 **/
static gboolean
up_backend_envsys_sensor_usable (prop_dictionary_t sensor)
{
	const char *state;

	if (sensor == NULL)
		return FALSE;
	if (!prop_dictionary_get_string (sensor, "state", &state))
		return TRUE;
	return strcmp (state, "invalid") != 0 && strcmp (state, "unknown") != 0;
}

/**
 * up_backend_envsys_sensor_value:
 *
 * Reads "cur-value" of a usable sensor.
 * Returns FALSE when the sensor is absent or carries no value.
 **/
static gboolean
up_backend_envsys_sensor_value (prop_array_t array, const char *description, gint64 *value)
{
	prop_dictionary_t sensor;

	sensor = up_backend_envsys_sensor (array, description);
	if (!up_backend_envsys_sensor_usable (sensor))
		return FALSE;
	return prop_dictionary_get_int64 (sensor, "cur-value", value);
}

/**
 * up_backend_envsys_sensor_is_amp:
 *
 * Returns TRUE when the capacity sensor reports Ampere hour units.
 **/
static gboolean
up_backend_envsys_sensor_is_amp (prop_array_t array, const char *description)
{
	prop_dictionary_t sensor;
	const char *type;

	sensor = up_backend_envsys_sensor (array, description);
	if (sensor == NULL)
		return FALSE;
	if (!prop_dictionary_get_string (sensor, "type", &type))
		return FALSE;
	return strcmp (type, "Ampere hour") == 0;
}

/**
 * up_backend_envsys_read_battery:
 *
 * Decodes the acpibat(4) sensor array. All envsys values use micro units.
 **/
static void
up_backend_envsys_read_battery (prop_array_t array, UpEnvsysBattery *bat)
{
	gint64 value;

	memset (bat, 0, sizeof (*bat));

	if (up_backend_envsys_sensor_value (array, "present", &value))
		bat->present = (value != 0);
	if (up_backend_envsys_sensor_value (array, "charging", &value))
		bat->charging = (value != 0);
	if (up_backend_envsys_sensor_value (array, "charge state", &value))
		bat->charge_state = (gint) value;
	if (up_backend_envsys_sensor_value (array, "design voltage", &value))
		bat->design_voltage = value / 1000000.0;
	if (up_backend_envsys_sensor_value (array, "voltage", &value))
		bat->voltage = value / 1000000.0;
	if (up_backend_envsys_sensor_value (array, "design cap", &value))
		bat->design_cap = value / 1000000.0;
	if (up_backend_envsys_sensor_value (array, "last full cap", &value))
		bat->last_full_cap = value / 1000000.0;
	if (up_backend_envsys_sensor_value (array, "charge", &value))
		bat->charge = value / 1000000.0;
	if (up_backend_envsys_sensor_value (array, "charge rate", &value) && value > 0)
		bat->rate = value / 1000000.0;
	/* acpibat(4) marks the discharge rate usable only while discharging. */
	bat->discharging = up_backend_envsys_sensor_usable (
	    up_backend_envsys_sensor (array, "discharge rate"));
	if (bat->discharging && up_backend_envsys_sensor_value (array, "discharge rate", &value) && value > 0)
		bat->rate = value / 1000000.0;
	bat->amp_hours = up_backend_envsys_sensor_is_amp (array, "charge");
}

/**
 * up_backend_envsys_ac_online:
 *
 * Reads the AC adapters of the same envsys dictionary. Sets @have_ac when
 * at least one adapter exists and returns TRUE when one is connected.
 **/
static gboolean
up_backend_envsys_ac_online (prop_dictionary_t dict, gboolean *have_ac)
{
	prop_object_iterator_t iter;
	prop_object_t key;
	gboolean online = FALSE;

	*have_ac = FALSE;
	iter = prop_dictionary_iterator (dict);
	if (iter == NULL)
		return FALSE;
	while ((key = prop_object_iterator_next (iter)) != NULL) {
		prop_object_t array = prop_dictionary_get_keysym (dict, key);
		const char *class_name;
		gint64 value;

		if (prop_object_type (array) != PROP_TYPE_ARRAY)
			continue;
		class_name = up_backend_envsys_device_class (array);
		if (class_name == NULL || strcmp (class_name, "ac-adapter") != 0)
			continue;
		*have_ac = TRUE;
		if (up_backend_envsys_sensor_value (array, "connected", &value) && value != 0)
			online = TRUE;
	}
	prop_object_iterator_release (iter);
	return online;
}

/**
 * up_backend_update_battery:
 **/
static void
up_backend_update_battery (UpDevice *device, prop_dictionary_t dict, prop_array_t array)
{
	UpEnvsysBattery bat;
	UpDeviceState state;
	gdouble volt, energy, energy_full, energy_full_design, rate;
	gdouble percentage = 0.0, capacity = 0.0;
	gint64 time_to_empty = 0, time_to_full = 0;
	gboolean have_ac, ac_online;

	up_backend_envsys_read_battery (array, &bat);
	ac_online = up_backend_envsys_ac_online (dict, &have_ac);

	g_object_set (device,
		      "is-present", bat.present,
		      "update-time", (guint64) (g_get_real_time () / G_USEC_PER_SEC),
		      NULL);
	if (!bat.present) {
		g_object_set (device,
			      "state", UP_DEVICE_STATE_UNKNOWN,
			      "percentage", 0.0,
			      "energy", 0.0,
			      "energy-rate", 0.0,
			      "time-to-empty", (gint64) 0,
			      "time-to-full", (gint64) 0,
			      NULL);
		return;
	}

	volt = bat.voltage;
	energy = bat.charge;
	energy_full = bat.last_full_cap;
	energy_full_design = bat.design_cap;
	rate = bat.rate;

	if (bat.amp_hours) {
		gdouble factor = bat.design_voltage;
		if (factor <= 0.0)
			factor = volt;
		if (factor <= 0.0)
			factor = 1.0;
		energy *= factor;
		energy_full *= factor;
		energy_full_design *= factor;
		rate *= factor;
	}

	/* A battery that reports no last full capacity uses its design value. */
	if (energy_full <= 0.0)
		energy_full = energy_full_design;

	if (energy_full > 0.0) {
		percentage = CLAMP (energy / energy_full * 100.0, 0.0, 100.0);
		if (energy_full_design > 0.0)
			capacity = CLAMP (energy_full / energy_full_design * 100.0, 0.0, 100.0);
	}

	/*
	 * acpibat(4) reports charging and discharging from _BST. A battery
	 * that does neither is full when its charge reaches the full capacity;
	 * otherwise the charger holds it (pending charge). Without an AC
	 * adapter device the _BST discharging flag is the only source.
	 */
	if (bat.charging) {
		state = UP_DEVICE_STATE_CHARGING;
		if (rate > 0.0 && energy_full > energy)
			time_to_full = (gint64) (3600.0 * (energy_full - energy) / rate);
	} else if (bat.discharging || (have_ac && !ac_online)) {
		state = UP_DEVICE_STATE_DISCHARGING;
		if (rate > 0.0)
			time_to_empty = (gint64) (3600.0 * energy / rate);
	} else if (bat.charge_state == ENVSYS_BATTERY_CAPACITY_MAX ||
		   bat.charge_state == ENVSYS_BATTERY_CAPACITY_HIGH ||
		   percentage >= 98.0) {
		state = UP_DEVICE_STATE_FULLY_CHARGED;
	} else {
		state = UP_DEVICE_STATE_PENDING_CHARGE;
	}
	if (bat.charge_state == ENVSYS_BATTERY_CAPACITY_CRITICAL &&
	    state == UP_DEVICE_STATE_DISCHARGING && energy <= 0.0)
		state = UP_DEVICE_STATE_EMPTY;

	if (time_to_full > UP_BACKEND_MAX_TIME)
		time_to_full = 0;
	if (time_to_empty > UP_BACKEND_MAX_TIME)
		time_to_empty = 0;

	g_object_set (device,
		      "state", state,
		      "percentage", percentage,
		      "energy", energy,
		      "energy-full", energy_full,
		      "energy-full-design", energy_full_design,
		      "energy-rate", rate,
		      "voltage", volt,
		      "capacity", capacity,
		      "time-to-empty", time_to_empty,
		      "time-to-full", time_to_full,
		      NULL);
}

/**
 * up_backend_update_ac:
 **/
static void
up_backend_update_ac (UpDevice *device, prop_array_t array)
{
	gint64 value;
	gboolean online = FALSE;

	if (up_backend_envsys_sensor_value (array, "connected", &value))
		online = (value != 0);
	g_object_set (device,
		      "online", online,
		      "update-time", (guint64) (g_get_real_time () / G_USEC_PER_SEC),
		      NULL);
}

static gboolean
up_envsys_device_get_on_battery (UpDevice *device, gboolean *on_battery)
{
	UpDeviceKind type;
	UpDeviceState state;
	gboolean is_present;

	g_return_val_if_fail (on_battery != NULL, FALSE);

	g_object_get (device,
		      "type", &type,
		      "state", &state,
		      "is-present", &is_present,
		      NULL);

	if (type != UP_DEVICE_KIND_BATTERY)
		return FALSE;
	if (state == UP_DEVICE_STATE_UNKNOWN)
		return FALSE;
	if (!is_present)
		return FALSE;

	*on_battery = (state == UP_DEVICE_STATE_DISCHARGING);
	return TRUE;
}

static gboolean
up_envsys_device_get_online (UpDevice *device, gboolean *online)
{
	UpDeviceKind type;
	gboolean online_tmp;

	g_return_val_if_fail (online != NULL, FALSE);

	g_object_get (device,
		      "type", &type,
		      "online", &online_tmp,
		      NULL);

	if (type != UP_DEVICE_KIND_LINE_POWER)
		return FALSE;

	*online = online_tmp;
	return TRUE;
}

/**
 * up_envsys_device_refresh:
 *
 * Re-reads the envsys dictionary and updates this device.
 **/
static gboolean
up_envsys_device_refresh (UpDevice *device, UpRefreshReason reason)
{
	UpEnvsysNative *native;
	UpDeviceKind type;
	prop_dictionary_t dict;
	prop_array_t array;
	gboolean ret = FALSE;

	native = UP_ENVSYS_NATIVE (up_device_get_native (device));
	dict = up_backend_envsys_fetch ();
	if (dict == NULL)
		return FALSE;

	array = prop_dictionary_get (dict, up_envsys_native_get_device (native));
	if (array == NULL || prop_object_type (array) != PROP_TYPE_ARRAY) {
		g_debug ("envsys device %s is gone", up_envsys_native_get_device (native));
		goto out;
	}

	g_object_get (device, "type", &type, NULL);
	switch (type) {
	case UP_DEVICE_KIND_BATTERY:
		up_backend_update_battery (device, dict, array);
		ret = TRUE;
		break;
	case UP_DEVICE_KIND_LINE_POWER:
		up_backend_update_ac (device, array);
		ret = TRUE;
		break;
	default:
		break;
	}
out:
	prop_object_release (dict);
	return ret;
}

/**
 * up_backend_add_device:
 *
 * Creates one UpDevice for an envsys device and announces it.
 **/
static void
up_backend_add_device (UpBackend *backend, const char *name, UpDeviceKind kind)
{
	UpEnvsysNative *native;
	UpDevice *device;
	UpDeviceClass *device_class;
	guint64 current_time;

	native = up_envsys_native_new (name);
	device = up_device_new (backend->priv->daemon, G_OBJECT (native));
	g_object_unref (native);

	/* The class is shared by all UpDevice instances of this backend. */
	device_class = UP_DEVICE_GET_CLASS (device);
	device_class->get_on_battery = up_envsys_device_get_on_battery;
	device_class->get_online = up_envsys_device_get_online;
	device_class->refresh = up_envsys_device_refresh;

	current_time = g_get_real_time () / G_USEC_PER_SEC;
	if (kind == UP_DEVICE_KIND_BATTERY) {
		g_object_set (device,
			      "type", UP_DEVICE_KIND_BATTERY,
			      "power-supply", TRUE,
			      "is-present", FALSE,
			      "is-rechargeable", TRUE,
			      "has-history", TRUE,
			      "has-statistics", TRUE,
			      "state", UP_DEVICE_STATE_UNKNOWN,
			      "percentage", 0.0,
			      "time-to-empty", (gint64) 0,
			      "update-time", current_time,
			      "poll-timeout", UP_BACKEND_REFRESH_TIMEOUT,
			      NULL);
	} else {
		g_object_set (device,
			      "type", UP_DEVICE_KIND_LINE_POWER,
			      "power-supply", TRUE,
			      "online", FALSE,
			      "update-time", current_time,
			      "poll-timeout", UP_BACKEND_REFRESH_TIMEOUT,
			      NULL);
	}

	if (!g_initable_init (G_INITABLE (device), NULL, NULL)) {
		g_warning ("failed to coldplug %s", name);
		g_object_unref (device);
		return;
	}
	g_ptr_array_add (backend->priv->devices, device);
	g_signal_emit (backend, signals[SIGNAL_DEVICE_ADDED], 0, device);
}

/**
 * up_backend_coldplug:
 * @backend: The %UpBackend class instance
 * @daemon: The %UpDaemon controlling instance
 *
 * Finds AC adapters first, so battery state can read the line power state.
 * Return value: %TRUE for success
 **/
gboolean
up_backend_coldplug (UpBackend *backend, UpDaemon *daemon)
{
	prop_dictionary_t dict;
	prop_object_iterator_t iter;
	prop_object_t key;
	GPtrArray *batteries;
	guint i;

	backend->priv->daemon = g_object_ref (daemon);

	dict = up_backend_envsys_fetch ();
	if (dict == NULL)
		return TRUE;

	batteries = g_ptr_array_new_with_free_func (g_free);
	iter = prop_dictionary_iterator (dict);
	while (iter != NULL && (key = prop_object_iterator_next (iter)) != NULL) {
		const char *name = prop_dictionary_keysym_value (key);
		prop_object_t array = prop_dictionary_get_keysym (dict, key);
		const char *class_name;

		if (prop_object_type (array) != PROP_TYPE_ARRAY)
			continue;
		class_name = up_backend_envsys_device_class (array);
		if (class_name == NULL)
			continue;
		if (strcmp (class_name, "ac-adapter") == 0)
			up_backend_add_device (backend, name, UP_DEVICE_KIND_LINE_POWER);
		else if (strcmp (class_name, "battery") == 0)
			g_ptr_array_add (batteries, g_strdup (name));
	}
	if (iter != NULL)
		prop_object_iterator_release (iter);
	prop_object_release (dict);

	for (i = 0; i < batteries->len; i++)
		up_backend_add_device (backend, g_ptr_array_index (batteries, i), UP_DEVICE_KIND_BATTERY);
	g_ptr_array_unref (batteries);

	return TRUE;
}

/**
 * up_backend_unplug:
 * @backend: The %UpBackend class instance
 *
 * Forget about all learned devices, effectively undoing up_backend_coldplug.
 * Resources are released without emitting signals.
 */
void
up_backend_unplug (UpBackend *backend)
{
	g_ptr_array_set_size (backend->priv->devices, 0);
	g_clear_object (&backend->priv->daemon);
}

/**
 * up_backend_get_seat_manager_proxy:
 * @backend: The %UpBackend class instance
 *
 * Returns the seat manager object or NULL on error. [transfer none]
 */
GDBusProxy *
up_backend_get_seat_manager_proxy (UpBackend  *backend)
{
	g_return_val_if_fail (UP_IS_BACKEND (backend), NULL);

	return backend->priv->seat_manager_proxy;
}

/**
 * up_backend_get_config:
 * @backend: The %UpBackend class instance
 *
 * Returns the UpConfig object or NULL on error. [transfer none]
 */
UpConfig *
up_backend_get_config (UpBackend  *backend)
{
	g_return_val_if_fail (UP_IS_BACKEND (backend), NULL);

	return backend->priv->config;
}

/**
 * up_backend_new:
 *
 * Return value: a new %UpBackend object.
 **/
UpBackend *
up_backend_new (void)
{
	return g_object_new (UP_TYPE_BACKEND, NULL);
}

static void
up_backend_class_init (UpBackendClass *klass)
{
	GObjectClass *object_class = G_OBJECT_CLASS (klass);
	object_class->finalize = up_backend_finalize;

	signals [SIGNAL_DEVICE_ADDED] =
		g_signal_new ("device-added",
			      G_TYPE_FROM_CLASS (object_class), G_SIGNAL_RUN_LAST,
			      G_STRUCT_OFFSET (UpBackendClass, device_added),
			      NULL, NULL, NULL,
			      G_TYPE_NONE, 1, UP_TYPE_DEVICE);
	signals [SIGNAL_DEVICE_REMOVED] =
		g_signal_new ("device-removed",
			      G_TYPE_FROM_CLASS (object_class), G_SIGNAL_RUN_LAST,
			      G_STRUCT_OFFSET (UpBackendClass, device_removed),
			      NULL, NULL, NULL,
			      G_TYPE_NONE, 1, UP_TYPE_DEVICE);
}

static void
up_backend_init (UpBackend *backend)
{
	backend->priv = up_backend_get_instance_private (backend);
	backend->priv->config = up_config_new ();
	backend->priv->devices = g_ptr_array_new_with_free_func (g_object_unref);
	backend->priv->seat_manager_proxy = g_dbus_proxy_new_for_bus_sync (G_BUS_TYPE_SYSTEM,
									   0,
									   NULL,
									   CONSOLEKIT2_DBUS_NAME,
									   CONSOLEKIT2_DBUS_PATH,
									   CONSOLEKIT2_DBUS_INTERFACE,
									   NULL,
									   NULL);
}

static void
up_backend_finalize (GObject *object)
{
	UpBackend *backend;

	g_return_if_fail (UP_IS_BACKEND (object));

	backend = UP_BACKEND (object);

	g_clear_object (&backend->priv->config);
	g_clear_object (&backend->priv->daemon);
	g_clear_pointer (&backend->priv->devices, g_ptr_array_unref);
	g_clear_object (&backend->priv->seat_manager_proxy);

	G_OBJECT_CLASS (up_backend_parent_class)->finalize (object);
}
