/* SPDX-License-Identifier: BSD-2-Clause */
/* Origin: EmberBSD (AI-assisted). Test boundary for external seat resources. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wayland-server-core.h>
#include "list.h"

static void *owned[32];
static unsigned live;

static void *
tracked_malloc(size_t size)
{

	assert(live < 32);
	void *p = malloc(size);
	assert(p != NULL);
	owned[live++] = p;
	return p;
}

static void
tracked_free(void *p)
{

	if (!p)
		return;
	unsigned i;
	for (i = 0; i < live && owned[i] != p; i++)
		continue;
	assert(i < live);
	owned[i] = owned[--live];
	free(p);
}

#define malloc tracked_malloc
#define free tracked_free

/* Model only the external resource types used by the actual handler. */
struct scene_node { unsigned marker; };
struct scene_tree { struct scene_node node; };
struct sway_seat_device { struct wl_list link; };
struct sway_seat_node { struct wl_list link; };
struct sway_seat {
	struct wl_listener destroy, new_node, request_start_drag, start_drag;
	struct wl_listener request_set_selection, request_set_primary_selection;
	struct wl_list devices, focus_stack, link;
	unsigned im_relay;
	unsigned *cursor;
	struct scene_tree *scene_tree;
	list_t *deferred_bindings;
	char *prev_workspace_name;
};
struct sway_config { struct { struct sway_seat *seat; } handler_context; };
static struct sway_config *config;
static struct sway_seat *active;
static struct sway_seat fallback, other;
static unsigned default_calls, devices, nodes, relays, cursors, scenes, bindings;

static struct sway_seat *
input_manager_get_default_seat(void)
{

	default_calls++;
	return &fallback;
}

static void
seat_device_destroy(struct sway_seat_device *device)
{

	assert(device != NULL);
	wl_list_remove(&device->link);
	free(device);
	devices++;
}

static void
seat_node_destroy(struct sway_seat_node *node)
{

	assert(node != NULL);
	wl_list_remove(&node->link);
	free(node);
	nodes++;
}

static void
sway_input_method_relay_finish(unsigned *relay)
{

	assert(relay == &active->im_relay && *relay == 42);
	relays++;
}

static void
sway_cursor_destroy(unsigned *cursor)
{

	assert(cursor == active->cursor && *cursor == 42);
	free(cursor);
	cursors++;
}

static void
wlr_scene_node_destroy(struct scene_node *node)
{

	assert(node == &active->scene_tree->node && node->marker == 42);
	free(node);
	scenes++;
}

static void
free_sway_binding(void *binding)
{

	assert(*(unsigned *)binding == 42);
	free(binding);
	bindings++;
}

/* ACTUAL HANDLER */

int
main(int argc, char **argv)
{
	struct sway_config storage = {0};
	struct sway_seat *seat = malloc(sizeof(*seat));
	struct sway_seat_device *device = malloc(sizeof(*device));
	struct sway_seat_node *node = malloc(sizeof(*node));

	assert(argc == 2);
	memset(seat, 0, sizeof(*seat));
	active = seat;
	wl_list_init(&seat->devices);
	wl_list_insert(&seat->devices, &device->link);
	wl_list_init(&seat->focus_stack);
	wl_list_insert(&seat->focus_stack, &node->link);
	wl_list_init(&seat->link);
	struct wl_listener *listeners[] = { &seat->destroy, &seat->new_node,
		&seat->request_start_drag, &seat->start_drag,
		&seat->request_set_selection, &seat->request_set_primary_selection };
	for (unsigned i = 0; i < sizeof(listeners) / sizeof(*listeners); i++)
		wl_list_init(&listeners[i]->link);
	seat->im_relay = 42;
	seat->cursor = malloc(sizeof(*seat->cursor));
	*seat->cursor = 42;
	seat->scene_tree = malloc(sizeof(*seat->scene_tree));
	seat->scene_tree->node.marker = 42;
	seat->prev_workspace_name = malloc(2);
	memcpy(seat->prev_workspace_name, "7", 2);
	seat->deferred_bindings = create_list();
	assert(seat->deferred_bindings && seat->deferred_bindings->items);
	for (unsigned i = 0; i < 2; i++) {
		unsigned *binding = malloc(sizeof(*binding));
		*binding = 42;
		list_add(seat->deferred_bindings, binding);
	}
	if (strcmp(argv[1], "absent") == 0) {
		config = NULL;
	} else {
		assert(strcmp(argv[1], "current") == 0 || strcmp(argv[1], "other") == 0);
		config = &storage;
		config->handler_context.seat = strcmp(argv[1], "current") == 0 ? seat : &other;
	}
	handle_seat_destroy(&seat->destroy, NULL);
	assert(live == 0);
	assert(devices == 1 && nodes == 1 && relays == 1 && cursors == 1);
	assert(scenes == 1 && bindings == 2);
	assert(default_calls == (unsigned)(strcmp(argv[1], "current") == 0));
	if (config)
		assert(config->handler_context.seat == (default_calls ? &fallback : &other));
	puts("PASS: complete seat cleanup and handler context ownership");
	return 0;
}
