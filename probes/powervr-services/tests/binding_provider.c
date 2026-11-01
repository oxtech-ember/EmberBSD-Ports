/* Origin: EmberBSD; AI-assisted foreign ELF ABI probe. */
/* SPDX-License-Identifier: BSD-2-Clause */

int probe_binding_marker(void);
int pvr_probe_binding_marker(void);

int
probe_binding_marker(void)
{
	return 29;
}

int
pvr_probe_binding_marker(void)
{
	return 29;
}
