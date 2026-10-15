/* SPDX-License-Identifier: MIT */
#include <ncnn/c_api.h>
#include <stddef.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>

#ifdef __cplusplus
#define HEADER_ALIGNOF(type) alignof(type)
#else
#define HEADER_ALIGNOF(type) _Alignof(type)
#endif
#define TYPE_LAYOUT(type) sizeof(struct type), HEADER_ALIGNOF(struct type)
#define FIELD(type, field) offsetof(struct type, field)

/* Keep the same externally named object in strict C and strict C++. */
extern const uint64_t ncnn_header_layout[];
const uint64_t ncnn_header_layout[] __attribute__((used, section(".ncnn_abi"))) = {
	UINT64_C(0x4e434e4e41424931), NCNN_VERSION_NUMBER, sizeof(void *), sizeof(size_t),
	TYPE_LAYOUT(__ncnn_allocator_t),
	FIELD(__ncnn_allocator_t, pthis),
	FIELD(__ncnn_allocator_t, fast_malloc),
	FIELD(__ncnn_allocator_t, fast_free),
	TYPE_LAYOUT(__ncnn_datareader_t),
	FIELD(__ncnn_datareader_t, pthis),
#if NCNN_STRING
	FIELD(__ncnn_datareader_t, scan),
#endif
	FIELD(__ncnn_datareader_t, read),
	TYPE_LAYOUT(__ncnn_modelbin_t),
	FIELD(__ncnn_modelbin_t, pthis),
	FIELD(__ncnn_modelbin_t, load_1d),
	FIELD(__ncnn_modelbin_t, load_2d),
	FIELD(__ncnn_modelbin_t, load_3d),
	TYPE_LAYOUT(__ncnn_layer_t),
	FIELD(__ncnn_layer_t, pthis),
	FIELD(__ncnn_layer_t, load_param),
	FIELD(__ncnn_layer_t, load_model),
	FIELD(__ncnn_layer_t, create_pipeline),
	FIELD(__ncnn_layer_t, destroy_pipeline),
	FIELD(__ncnn_layer_t, forward_1),
	FIELD(__ncnn_layer_t, forward_n),
	FIELD(__ncnn_layer_t, forward_inplace_1),
	FIELD(__ncnn_layer_t, forward_inplace_n)
};

int
main(void)
{
	size_t i;
	for (i = 0; i < sizeof(ncnn_header_layout) / sizeof(ncnn_header_layout[0]); i++)
		if (printf("%" PRIu64 "\n", ncnn_header_layout[i]) < 0)
			return (1);
	return (0);
}
