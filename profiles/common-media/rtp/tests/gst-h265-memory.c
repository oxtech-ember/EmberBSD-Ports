/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 EmberBSD contributors (AI-assisted).
 * Exercise ordinary GstMemory mapping failure against the real RTP helper.
 * Link the owning upstream depayloader, utilities and element-init objects.
 */
#include <gst/gst.h>
#include <stdio.h>
#include <string.h>

GType gst_rtp_h265_depay_get_type(void);
gboolean gst_rtp_h265_add_vps_sps_pps(GstElement *, GPtrArray *, GPtrArray *,
    GPtrArray *, GstBuffer *);

typedef struct {
	GstAllocator parent;
} E35Allocator;
typedef struct {
	GstAllocatorClass parent;
} E35AllocatorClass;
typedef struct {
	GstMemory parent;
	gboolean readable;
	guint8 data[16];
} E35Memory;

static unsigned int live_memory, successful_maps, unmaps;
GType e35_allocator_get_type(void);
G_DEFINE_TYPE(E35Allocator, e35_allocator, GST_TYPE_ALLOCATOR)

static gpointer
memory_map(GstMemory *memory, gsize maximum, GstMapFlags flags)
{
	E35Memory *owned = (E35Memory *)memory;

	(void)maximum;
	(void)flags;
	if (!owned->readable)
		return NULL;
	successful_maps++;
	return owned->data;
}

static void
memory_unmap(GstMemory *memory)
{
	(void)memory;
	unmaps++;
}

static GstMemory *
memory_alloc(GstAllocator *allocator, gsize size, GstAllocationParams *params)
{
	E35Memory *memory;

	if (size > 16 || params->prefix != 0 || params->padding != 0)
		return NULL;
	memory = g_new0(E35Memory, 1);
	memory->readable = TRUE;
	gst_memory_init(&memory->parent, 0, allocator, NULL, size, 0, 0, size);
	live_memory++;
	return &memory->parent;
}

static void
memory_free(GstAllocator *allocator, GstMemory *memory)
{
	(void)allocator;
	live_memory--;
	g_free(memory);
}

static void
e35_allocator_class_init(E35AllocatorClass *klass)
{
	GstAllocatorClass *allocator = GST_ALLOCATOR_CLASS(klass);

	allocator->alloc = memory_alloc;
	allocator->free = memory_free;
}

static void
e35_allocator_init(E35Allocator *owned)
{
	GstAllocator *allocator = GST_ALLOCATOR(owned);

	allocator->mem_type = "EmberBSD parameter-set memory";
	allocator->mem_map = memory_map;
	allocator->mem_unmap = memory_unmap;
}

static GstBuffer *
parameter_set(GstAllocator *allocator, unsigned int type, E35Memory **memory)
{
	GstAllocationParams params;
	GstMemory *allocated;
	GstBuffer *buffer;
	gsize size;

	size = type == 33 ? 16 : 3;
	gst_allocation_params_init(&params);
	allocated = gst_allocator_alloc(allocator, size, &params);
	if (allocated == NULL)
		return NULL;
	*memory = (E35Memory *)allocated;
	(*memory)->data[0] = (guint8)(type << 1);
	(*memory)->data[1] = 1;
	(*memory)->data[size - 1] = type == 34 ? 0xc0 : 0x80;
	buffer = gst_buffer_new();
	gst_buffer_append_memory(buffer, allocated);
	return buffer;
}

int
main(int argc, char **argv)
{
	GstAllocator *allocator;
	GstElement *element;
	GPtrArray *vps, *sps, *pps, *selected;
	GstBuffer *incoming;
	E35Memory *cached, *fresh;
	gboolean result;
	unsigned int type;
	int status = 1;

	if (argc != 2 || (strcmp(argv[1], "normal") != 0 &&
	    strcmp(argv[1], "input-unavailable") != 0 &&
	    strcmp(argv[1], "cached-unavailable") != 0))
		return 2;
	gst_init(NULL, NULL);
	(void)g_log_set_always_fatal(G_LOG_FATAL_MASK | G_LOG_LEVEL_CRITICAL);
	allocator = g_object_new(e35_allocator_get_type(), NULL);
	element = g_object_new(gst_rtp_h265_depay_get_type(), NULL);
	vps = g_ptr_array_new_with_free_func((GDestroyNotify)gst_buffer_unref);
	sps = g_ptr_array_new_with_free_func((GDestroyNotify)gst_buffer_unref);
	pps = g_ptr_array_new_with_free_func((GDestroyNotify)gst_buffer_unref);
	for (type = 32; type <= 34; type++) {
		selected = type == 32 ? vps : type == 33 ? sps : pps;
		incoming = parameter_set(allocator, type, &cached);
		if (incoming == NULL)
			goto done;
		if (strcmp(argv[1], "input-unavailable") == 0) {
			cached->readable = FALSE;
			result = gst_rtp_h265_add_vps_sps_pps(element, vps, sps, pps,
			    incoming);
			if (result || selected->len != 0)
				goto done;
			continue;
		}
		if (!gst_rtp_h265_add_vps_sps_pps(element, vps, sps, pps, incoming) ||
		    selected->len != 1)
			goto done;
		if (strcmp(argv[1], "cached-unavailable") == 0)
			cached->readable = FALSE;
		incoming = parameter_set(allocator, type, &fresh);
		if (incoming == NULL)
			goto done;
		result = gst_rtp_h265_add_vps_sps_pps(element, vps, sps, pps,
		    incoming);
		if (result || selected->len != 1 ||
		    (E35Memory *)gst_buffer_peek_memory(
		    g_ptr_array_index(selected, 0), 0) != cached)
			goto done;
		cached->readable = TRUE;
	}
	status = 0;
done:
	g_ptr_array_unref(vps);
	g_ptr_array_unref(sps);
	g_ptr_array_unref(pps);
	gst_object_unref(element);
	gst_object_unref(allocator);
	gst_deinit();
	if (live_memory != 0 || successful_maps != unmaps)
		status = 1;
	printf("{\"ok\":%s,\"live_memory\":%u,\"maps\":%u,\"unmaps\":%u}\n",
	    status == 0 ? "true" : "false", live_memory, successful_maps, unmaps);
	return status;
}
