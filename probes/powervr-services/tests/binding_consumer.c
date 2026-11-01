/* Origin: EmberBSD; AI-assisted foreign ELF ABI probe. */
/* SPDX-License-Identifier: BSD-2-Clause */

#ifdef PROBE_NAMESPACED
int pvr_probe_binding_marker(void);
#define BINDING_MARKER pvr_probe_binding_marker
#else
int probe_binding_marker(void);
#define BINDING_MARKER probe_binding_marker
#endif
int probe_consumer(void);

int
probe_consumer(void)
{
	return BINDING_MARKER();
}
