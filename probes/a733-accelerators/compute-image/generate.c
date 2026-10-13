/* SPDX-License-Identifier: MIT */
/* Copyright (c) 2026 EmberBSD contributors. */
/*
 * CPU allocation adapter for unchanged Mesa 26.2.4 producers.
 * It never opens a DRM device and never submits GPU work.
 * See README.md for source attribution, address policy, and acceptance limits.
 */
#include <assert.h>
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vulkan/vulkan_core.h>

#include "pvr_device_info.h"
#include "pvr_types.h"
#include "pvr_limits.h"
#include "util/bitset.h"
#include "util/format/u_format.h"
#include "util/log.h"
#include "vk_format.h"
#include "pvr_pds.h"
#include "hwdef/rogue_hw_utils.h"
#include "patched-pvr_iface.h"

#define __pvr_address_type pvr_dev_addr_t
#define __pvr_get_address(a) ((a).addr)
#define __pvr_make_address(a) PVR_DEV_ADDR(a)
#include "csbgen/rogue/kmd_stream.h"
#include "csbgen/rogue/cr.h"
#include "csbgen/rogue/pds.h"
#include "csbgen/rogue/vdm.h"
#include "csbgen/rogue/texstate.h"
#undef __pvr_address_type
#undef __pvr_get_address
#undef __pvr_make_address

#define PVR_WORKGROUP_DIMENSIONS 3U
#define ROGUE_NUM_SHADER_STATE_BUFFERS 2U
#define ROGUE_PDS_TASK_PROGRAM_SIZE 256U
#define PVR_PER_ARCH(n) pvr_rogue_##n
#define PIXEL_ALLOCATION_SIZE_MAX_IN_BLOCKS \
    (1024 / ROGUE_CDMCTRL_KERNEL0_USC_COMMON_SIZE_UNIT_SIZE)
#define pvr_cmd_length(x) ROGUE_##x##_length
#define pvr_cmd_header(x) ROGUE_##x##_header
#define pvr_cmd_pack(x) ROGUE_##x##_pack
#define pvr_csb_pack(dst, cmd, name) \
    for (struct ROGUE_##cmd name = { pvr_cmd_header(cmd) }, *loop = &name; \
        loop != NULL; pvr_cmd_pack(cmd)((dst), &name), loop = NULL)
#define pvr_csb_emit(csb, cmd, name) \
    for (struct ROGUE_##cmd name = { pvr_cmd_header(cmd) }, \
        *dst = csb_alloc((csb), pvr_cmd_length(cmd)); dst != NULL; \
        pvr_cmd_pack(cmd)(dst, &name), dst = NULL)

#define PVR_DW_TO_BYTES(n) ((n) * 4U)
#define _BITULL(n) (UINT64_C(1) << (n))
#define PVR_BO_ALLOC_FLAG_CPU_MAPPED 1U
#define BORDER_VA UINT64_C(0x8000010000)
#define GENERAL_BASE UINT64_C(0x8000000000)
#define PDS_BASE UINT64_C(0xda00000000)
/* DOUTU execution offsets are 30-bit fields: the USC code heap must
 * live below 4 GiB. 0x2000 matches the kernel's low mapping. */
#define USC_BASE UINT64_C(0x2000)
#define RESUME_OFFSET 0x1000U
#define TEXTURE_OFFSET 0x2000U
#define SHARED_OFFSET 0x3000U
#define STREAM_OFFSET 0x4000U
#define STATE_B_OFFSET 0x5000U
#define PROGRAM_OFFSET 0xa000U
#define REGION_CAPACITY 0x10000U

struct region {
	uint8_t *bytes;
	size_t used;
	uint64_t base;
};
struct pvr_reset_cmd { unsigned unused; };
/* CPU-only BO adapter for the unchanged border and command producers. */
struct pvr_winsys_bo { void *map; };
struct pvr_winsys_vma { pvr_dev_addr_t dev_addr; };
struct pvr_bo {
	struct pvr_winsys_bo *bo;
	struct pvr_winsys_vma *vma;
};

#include "mesa-types.h"
#include "mesa-precomp.h"

/* Only CPU adapter fields consumed by the extracted producers are present. */
struct pvr_physical_device {
	struct pvr_device_info dev_info;
	struct pvr_device_runtime_info dev_runtime_info;
};
struct pvr_device {
	struct pvr_physical_device *pdevice;
	struct { unsigned alloc; } vk;
	struct pvr_pds_upload pds_compute_fence_program;
	struct {
		uint32_t usc_shareds;
		struct pvr_pds_upload pds, sw_compute_barrier_pds;
	} idfwdf_state;
	struct region pds;
	struct { void *general_heap; } heaps;
	struct pvr_border_color_table *border_color_table;
	void *border_bytes;
	size_t border_size;
};
struct pvr_csb { uint32_t *words; size_t count, capacity; pvr_dev_addr_t start; };
struct pvr_sub_cmd_compute {
	struct pvr_csb control_stream;
	uint32_t num_shared_regs;
	bool pds_sw_barrier_requires_clearing;
	bool uses_atomic_ops, uses_barrier;
};
struct pvr_cmd_buffer_state {
	struct { struct pvr_sub_cmd_compute compute; } *current_sub_cmd;
};
struct pvr_cmd_buffer {
	struct pvr_device *device;
	struct pvr_cmd_buffer_state state;
};
struct shader {
	uint8_t *raw;
	size_t raw_size;
	uint8_t temps, vtxins;
	uint16_t coeffs, shareds, dwords;
	uint64_t offset;
};

static _Noreturn void
fail(const char *message)
{
	fprintf(stderr, "compute-image: %s\n", message);
	exit(EXIT_FAILURE);
}

static void *
csb_alloc(struct pvr_csb *csb, size_t words)
{
	void *result;

	if (words > csb->capacity - csb->count)
		fail("CDM buffer exceeds its allocation");
	result = csb->words + csb->count;
	csb->count += words;
	return result;
}

/* Relocations are already fixed in the immutable address map. */
static void pvr_csb_set_relocation_mark(struct pvr_csb *csb) { (void)csb; }
static void pvr_csb_clear_relocation_mark(struct pvr_csb *csb) { (void)csb; }
static void pvr_finishme(const char *message) { fail(message); }
static VkResult vk_error(void *dev, VkResult error)
{ (void)dev; return error; }
static void *vk_alloc(void *alloc, size_t size, size_t alignment, int scope)
{ (void)alloc; (void)alignment; (void)scope; return calloc(1, size); }
static void *vk_realloc(void *alloc, void *ptr, size_t size,
    size_t alignment, int scope)
{ (void)alloc; (void)alignment; (void)scope; return realloc(ptr, size); }
static void vk_free(void *alloc, void *ptr) { (void)alloc; free(ptr); }
static void pvr_bo_suballoc_free(struct pvr_suballoc_bo *bo)
{ if (bo != NULL) fail("unexpected GPU allocation in CPU adapter"); }

static void *
vk_zalloc(void *alloc, size_t size, size_t alignment, int scope)
{
	return vk_alloc(alloc, size, alignment, scope);
}

static VkResult
pvr_bo_alloc(struct pvr_device *device, void *heap, uint64_t size,
    uint64_t alignment, uint32_t flags, struct pvr_bo **out)
{
	struct pvr_bo *bo;

	if (heap != device->heaps.general_heap || device->border_bytes != NULL ||
	    size == 0 || size > 512 * 1024 || alignment != 64 ||
	    flags != PVR_BO_ALLOC_FLAG_CPU_MAPPED)
		fail("unsupported border allocation");
	bo = calloc(1, sizeof(*bo));
	if (bo == NULL)
		return VK_ERROR_OUT_OF_HOST_MEMORY;
	bo->bo = calloc(1, sizeof(*bo->bo));
	bo->vma = calloc(1, sizeof(*bo->vma));
	device->border_bytes = calloc(1, (size_t)size);
	if (bo->bo == NULL || bo->vma == NULL || device->border_bytes == NULL)
		fail("cannot allocate CPU border table");
	bo->bo->map = device->border_bytes;
	bo->vma->dev_addr = PVR_DEV_ADDR(BORDER_VA);
	device->border_size = (size_t)size;
	*out = bo;
	return VK_SUCCESS;
}

static void
pvr_bo_cpu_unmap(struct pvr_device *device, struct pvr_bo *bo)
{
	if (bo->bo->map != device->border_bytes)
		fail("unexpected border mapping");
	/* The CPU image owner retains the allocation after the producer unmaps it. */
	bo->bo->map = NULL;
}

static pvr_dev_addr_t
pvr_csb_get_start_address(const struct pvr_csb *csb)
{
	return csb->start;
}

const uint8_t *pvr_get_format_swizzle_for_tpu(const struct util_format_description *);
#include "mesa-border.h"

/* pvr_device.c:pvr_gpu_upload_pds layout, with a bounded CPU arena. */
static VkResult
pvr_gpu_upload_pds(struct pvr_device *device, const uint32_t *data,
    uint32_t data_dw, uint32_t data_align, const uint32_t *code,
    uint32_t code_dw, uint32_t code_align, uint64_t minimum,
    struct pvr_pds_upload *out)
{
	size_t ds, cs, co, base, total, align;

	if (data == NULL || code == NULL || data_dw == 0 || code_dw == 0 ||
	    data_align == 0 || code_align == 0 ||
	    (data_align & (data_align - 1)) != 0 ||
	    (code_align & (code_align - 1)) != 0)
		return VK_ERROR_INITIALIZATION_FAILED;
	ds = ALIGN_POT((size_t)data_dw * 4, data_align);
	cs = ALIGN_POT((size_t)code_dw * 4, code_align);
	co = ALIGN_POT(ds, code_align);
	align = MAX2(minimum, data_align);
	if (align == 0 || (align & (align - 1)) != 0)
		return VK_ERROR_INITIALIZATION_FAILED;
	base = ALIGN_POT(device->pds.used, align);
	total = co + cs;
	if (base > REGION_CAPACITY || total > REGION_CAPACITY - base)
		return VK_ERROR_OUT_OF_HOST_MEMORY;
	memcpy(device->pds.bytes + base, data, (size_t)data_dw * 4);
	memcpy(device->pds.bytes + base + co, code, (size_t)code_dw * 4);
	*out = (struct pvr_pds_upload){ .data_offset = (uint32_t)base,
	    .code_offset = (uint32_t)(base + co), .data_size = (uint32_t)(ds / 4),
	    .code_size = (uint32_t)(cs / 4) };
	device->pds.used = base + total;
	return VK_SUCCESS;
}

#include "mesa-producers.h"
static struct pvr_device_info device_info;
#include "mesa-runtime.h"

static void
require_success(VkResult result)
{
	if (result != VK_SUCCESS)
		fail("Mesa producer rejected the input");
}

static void
load_shader(const char *path, struct shader *shader, struct region *usc)
{
	FILE *file;
	long length;
	size_t bytes, offset;
	pco_precomp_data metadata;

	file = fopen(path, "rb");
	if (file == NULL || fseek(file, 0, SEEK_END) != 0 ||
	    (length = ftell(file)) < 8 || length > REGION_CAPACITY ||
	    fseek(file, 0, SEEK_SET) != 0)
		fail("invalid compiler output file");
	shader->raw = calloc(1, (size_t)length);
	if (shader->raw == NULL)
		fail("cannot allocate shader input");
	if (fread(shader->raw, 1, (size_t)length, file) != (size_t)length ||
	    fclose(file) != 0)
		fail("cannot read compiler output");
	shader->raw_size = (size_t)length;
	/* Use the original compiler ABI, including its packed bit fields. */
	memcpy(&metadata, shader->raw, sizeof(metadata));
	shader->temps = metadata.temps;
	shader->vtxins = metadata.vtxins;
	shader->coeffs = metadata.coeffs;
	shader->shareds = metadata.shareds;
	shader->dwords = metadata.size_dwords;
	if (shader->dwords == 0 || shader->raw[7] != 0 ||
	    (size_t)shader->dwords * 4 != shader->raw_size - 8)
		fail("inconsistent pco_precomp_data size or padding");
	bytes = (size_t)shader->dwords * 4;
	offset = ALIGN_POT(usc->used, 64);
	if (offset > REGION_CAPACITY || bytes > REGION_CAPACITY - offset)
		fail("USC image exceeds its allocation");
	memcpy(usc->bytes + offset, shader->raw + 8, bytes);
	usc->used = offset + bytes;
	shader->offset = offset;
}

/* Exact fixed-format branch of pvr_arch_pack_tex_state, not a general API. */
static void
pack_idfwdf(struct pvr_device *device, uint32_t shared[10])
{
	const struct pvr_device_info *info = &device->pdevice->dev_info;
	uint64_t image[2], sampler[2];

	_Static_assert(PVR_IDFWDF_DATA_ADDR_LO == 8, "patched IDFWDF required");
	_Static_assert(_PVR_IDFWDF_DATA_COUNT == 10, "patched shader ABI required");
	pvr_csb_pack(&image[0], TEXSTATE_IMAGE_WORD0, word) {
		word.textype = ROGUE_TEXSTATE_TEXTYPE_STRIDE;
		word.texformat = ROGUE_TEXSTATE_FORMAT_F32F32F32F32;
		word.swiz0 = ROGUE_TEXSTATE_SWIZ_SRCCHAN_0;
		word.swiz1 = ROGUE_TEXSTATE_SWIZ_SRCCHAN_1;
		word.swiz2 = ROGUE_TEXSTATE_SWIZ_SRCCHAN_2;
		word.swiz3 = ROGUE_TEXSTATE_SWIZ_SRCCHAN_3;
		word.width = 3;
		word.height = 1;
	}
	pvr_csb_pack(&image[1], TEXSTATE_STRIDE_IMAGE_WORD1, word) {
		word.stride = 3;
		word.num_mip_levels = 1;
		word.texaddr = PVR_DEV_ADDR(GENERAL_BASE + TEXTURE_OFFSET);
		if (!PVR_HAS_FEATURE(info, tpu_extended_integer_lookup) &&
		    !PVR_HAS_FEATURE(info, tpu_image_state_v2))
			word.index_lookup = true;
	}
	pvr_csb_pack(&sampler[0], TEXSTATE_SAMPLER_WORD0, word) {
		word.dadjust = ROGUE_TEXSTATE_DADJUST_ZERO_UINT;
		word.magfilter = ROGUE_TEXSTATE_FILTER_POINT;
		word.addrmode_u = ROGUE_TEXSTATE_ADDRMODE_CLAMP_TO_EDGE;
		word.addrmode_v = ROGUE_TEXSTATE_ADDRMODE_CLAMP_TO_EDGE;
	}
	pvr_csb_pack(&sampler[1], TEXSTATE_SAMPLER_WORD1, word) {}
	memcpy(shared + PVR_IDFWDF_DATA_TEX, image, sizeof(image));
	memcpy(shared + PVR_IDFWDF_DATA_SMP, sampler, sizeof(sampler));
	shared[PVR_IDFWDF_DATA_ADDR_LO] = (uint32_t)(GENERAL_BASE + TEXTURE_OFFSET);
	shared[PVR_IDFWDF_DATA_ADDR_HI] = (GENERAL_BASE + TEXTURE_OFFSET) >> 32;
}

static void
write_file(const char *name, const void *bytes, size_t length)
{
	FILE *file = fopen(name, "wbx");
	if (file == NULL || fwrite(bytes, 1, length, file) != length ||
	    fclose(file) != 0)
		fail("cannot write new output file");
}

int
main(int argc, char **argv)
{
	struct pvr_physical_device physical = { 0 };
	struct pvr_device device = { .pdevice = &physical };
	struct pvr_compute_ctx context = { 0 };
	struct pvr_rogue_winsys_compute_ctx_static_state state = { 0 };
	struct pvr_pds_compute_shader_program primary, fence;
	struct pvr_pds_upload primary_upload;
	struct pvr_private_compute_pipeline pipeline = { 0 };
	struct pvr_sub_cmd_compute compute = { 0 };
	struct pvr_cmd_buffer cmd = { .device = &device };
	struct region general = { .base = GENERAL_BASE };
	struct region usc = { .base = USC_BASE };
	struct shader shaders[4] = { 0 };
	struct pvr_winsys_compute_submit_info submit = { 0 };
	struct pvr_winsys_vma resume_vma = { .dev_addr = PVR_DEV_ADDR(GENERAL_BASE + RESUME_OFFSET) };
	struct pvr_bo resume = { .vma = &resume_vma };
	uint64_t static_words[7];
	uint32_t command[12], command_flags;
	uint32_t groups[3] = { 1, 1, 1 };
	FILE *manifest;

	if (argc != 5)
		fail("usage: generate PROBE.precomp STORE.precomp LOAD.precomp IDFWDF.precomp");
	if (*(const uint8_t *)&(const uint16_t){ 1 } != 1)
		fail("only little-endian hosts are supported");
	if (pvr_device_info_init(&physical.dev_info,
	    PVR_BVNC_PACK(36, 56, 104, 183)) != 0)
		fail("exact BVNC is absent from Mesa");
	device_info = physical.dev_info;
	context.device = &device;
	context.ctx_switch.compute_state_bo = &resume;
	physical.dev_runtime_info.core_count = 1;
	physical.dev_runtime_info.num_phantoms = 1;
	physical.dev_runtime_info.cdm_max_local_mem_size_regs =
	    rogue_cdm_max_local_mem_size_regs(&physical.dev_info);
	if ((PVR_NEED_SW_COMPUTE_PDS_BARRIER(&physical.dev_info)) ||
	    PVR_HAS_QUIRK(&physical.dev_info, 62269) ||
	    pvr_get_slc_cache_line_size(&physical.dev_info) != 64)
		fail("profile outside initial producer scope");
	general.bytes = calloc(1, REGION_CAPACITY);
	device.pds.bytes = calloc(1, REGION_CAPACITY);
	usc.bytes = calloc(1, REGION_CAPACITY);
	if (general.bytes == NULL || device.pds.bytes == NULL || usc.bytes == NULL)
		fail("cannot allocate CPU images");
	device.pds.base = PDS_BASE;
	device.pds.used = PROGRAM_OFFSET;
	for (unsigned i = 0; i < 4; i++)
		load_shader(argv[i + 1], &shaders[i], &usc);
	if (shaders[0].vtxins != 0 || shaders[0].coeffs != 0 ||
	    shaders[0].shareds != 0)
		fail("probe inputs require an explicit supported metadata mapping");
	require_success(pvr_arch_border_color_table_init(&device));
	pack_idfwdf(&device, (uint32_t *)(general.bytes + SHARED_OFFSET));
	device.idfwdf_state.usc_shareds = _PVR_IDFWDF_DATA_COUNT;
	require_success(pvr_pds_idfwdf_programs_create_and_upload(&device,
	    PVR_DEV_ADDR(USC_BASE + shaders[3].offset), _PVR_IDFWDF_DATA_COUNT,
	    shaders[3].temps, PVR_DEV_ADDR(GENERAL_BASE + SHARED_OFFSET),
	    &device.idfwdf_state.pds, &device.idfwdf_state.sw_compute_barrier_pds));
	pvr_pds_compute_shader_program_init(&primary);
	primary.kick_usc = true;
	primary.flattened_work_groups = true;
	pvr_pds_setup_doutu(&primary.usc_task_control, shaders[0].offset,
	    shaders[0].temps, ROGUE_PDSINST_DOUTU_SAMPLE_RATE_INSTANCE, false);
	require_success(pvr_arch_pds_compute_shader_create_and_upload(&device,
	    &primary, &primary_upload));
	pvr_pds_compute_shader_program_init(&fence);
	fence.fence = true;
	fence.clear_pds_barrier = true;
	require_success(pvr_arch_pds_compute_shader_create_and_upload(&device,
	    &fence, &device.pds_compute_fence_program));
	for (unsigned i = 0; i < 2; i++) {
		uint64_t state_va = PDS_BASE + (i ? STATE_B_OFFSET : 0);
		context.ctx_switch.sr[i].usc.unified_size = DIV_ROUND_UP(64,
		    ROGUE_VDMCTRL_PDS_STATE0_USC_UNIFIED_SIZE_UNIT_SIZE);
		require_success(pvr_pds_compute_ctx_sr_program_create_and_upload(
		    &device, false, shaders[1].offset, shaders[1].temps,
		    PVR_DEV_ADDR(state_va), &context.ctx_switch.sr[i].pds.store_program));
		require_success(pvr_pds_compute_ctx_sr_program_create_and_upload(
		    &device, true, shaders[2].offset, shaders[2].temps,
		    PVR_DEV_ADDR(state_va), &context.ctx_switch.sr[i].pds.load_program));
	}
	require_success(pvr_pds_sr_fence_terminate_program_create_and_upload(
	    &device, &context.ctx_switch.sr_fence_terminate_program));
	pvr_compute_ctx_ws_static_state_init(&physical.dev_info, &context, &state);
	/* pvr_drm_compute_ctx_static_state_init, without the transport header. */
	static_words[0] = state.cdm_ctx_store_pds0;
	static_words[1] = state.cdm_ctx_store_pds1;
	static_words[2] = state.cdm_ctx_terminate_pds;
	static_words[3] = state.cdm_ctx_terminate_pds1;
	static_words[4] = state.cdm_ctx_resume_pds0;
	static_words[5] = state.cdm_ctx_store_pds0_b;
	static_words[6] = state.cdm_ctx_resume_pds0_b;
	pipeline.pds_code_offset = primary_upload.code_offset;
	pipeline.pds_data_offset = primary_upload.data_offset;
	pipeline.pds_data_size_dw = primary_upload.data_size;
	pipeline.pds_temps_used = primary.temps_used;
	pipeline.unified_store_regs_count = shaders[0].vtxins;
	pipeline.workgroup_size = (VkExtent3D){ 1, 1, 1 };
	compute.control_stream = (struct pvr_csb){
	    .words = (uint32_t *)(general.bytes + STREAM_OFFSET), .capacity = 1024,
	    .start = PVR_DEV_ADDR(GENERAL_BASE + STREAM_OFFSET) };
	cmd.state.current_sub_cmd = calloc(1, sizeof(*cmd.state.current_sub_cmd));
	if (cmd.state.current_sub_cmd == NULL)
		fail("cannot allocate command state");
	pvr_arch_compute_update_kernel_private(&cmd, &compute, &pipeline, groups);
	pvr_compute_generate_idfwdf(&cmd, &compute);
	pvr_arch_compute_generate_fence(&cmd, &compute, false);
	pvr_arch_compute_generate_fence(&cmd, &compute, true);
	pvr_csb_emit(&compute.control_stream, CDMCTRL_STREAM_TERMINATE, terminate) {}
	/* Export unchanged Mesa command fields after the CDM producer sets shareds. */
	pvr_submit_info_stream_init(&context, &compute, &submit);
	pvr_submit_info_flags_init(&physical.dev_info, &compute, &submit.flags);
	command_flags = pvr_winsys_compute_flags_to_drm(&submit.flags);
	if (submit.fw_stream_len != sizeof(command) - sizeof(command_flags) ||
	    PVR_HAS_QUIRK(&physical.dev_info, 49927))
		fail("unsupported firmware command extension");
	memcpy(command, submit.fw_stream, submit.fw_stream_len);
	command[11] = command_flags;
	write_file("command.bin", command, sizeof(command));
	write_file("border.bin", device.border_bytes, device.border_size);
	general.used = STREAM_OFFSET + compute.control_stream.count * 4;
	write_file("general.bin", general.bytes, general.used);
	write_file("pds.bin", device.pds.bytes, device.pds.used);
	write_file("usc.bin", usc.bytes, usc.used);
	write_file("static-state.bin", static_words, sizeof(static_words));
	manifest = fopen("producer.json", "wx");
	if (manifest == NULL)
		fail("cannot create producer manifest");
	fprintf(manifest, "{\n  \"bvnc\": \"36.56.104.183\",\n"
	    "  \"hardware_validated\": false,\n"
	    "  \"scratch_va\": \"0x8000000000\",\n"
	    "  \"resume_va\": \"0x8000001000\",\n"
	    "  \"stream_va\": \"0x8000004000\",\n"
	    "  \"cdm_bytes\": %zu,\n  \"cdm_local_x\": %u,\n"
	    "  \"cdm_max_local_mem_size_regs\": %u,\n"
	    "  \"usc_shared_registers\": %u,\n  \"shaders\": [\n",
	    compute.control_stream.count * 4, ROGUE_MAX_INSTANCES_PER_TASK,
	    (unsigned)physical.dev_runtime_info.cdm_max_local_mem_size_regs,
	    device.idfwdf_state.usc_shareds);
	for (unsigned i = 0; i < 4; i++) {
		fprintf(manifest, "    {\"offset\": %" PRIu64 ", \"temps\": %u, "
		    "\"vtxins\": %u, \"coeffs\": %u, \"shareds\": %u, "
		    "\"dwords\": %u}%s\n", shaders[i].offset, shaders[i].temps,
		    shaders[i].vtxins, shaders[i].coeffs, shaders[i].shareds,
		    shaders[i].dwords, i == 3 ? "" : ",");
		free(shaders[i].raw);
	}
	if (fprintf(manifest, "  ],\n  \"border_va\": \"0x%" PRIx64 "\",\n"
	    "  \"border_bytes\": %zu,\n  \"command_bytes\": %zu,\n"
	    "  \"command_stream_bytes\": %u,\n  \"command_drm_flags\": %u,\n"
	    "  \"resume_load_data_dwords\": %u,\n  \"resume_unified_size\": %u,\n"
	    "  \"command_shared_registers\": %u\n}\n",
	    BORDER_VA, device.border_size, sizeof(command), submit.fw_stream_len,
	    command_flags, context.ctx_switch.sr[0].pds.load_program.data_size,
	    context.ctx_switch.sr[0].usc.unified_size, compute.num_shared_regs) < 0 ||
	    fclose(manifest) != 0)
		fail("cannot complete producer manifest");
	free(device.border_color_table->table->bo);
	free(device.border_color_table->table->vma);
	free(device.border_color_table->table);
	free(device.border_color_table);
	free(device.border_bytes);
	free(cmd.state.current_sub_cmd);
	free(general.bytes);
	free(device.pds.bytes);
	free(usc.bytes);
	return EXIT_SUCCESS;
}
