/* Origin: EmberBSD; AI-assisted foreign ELF ABI probe. */
/* SPDX-License-Identifier: BSD-2-Clause */

int probe_tls_get(void);
void probe_tls_set(int);

#ifdef PROBE_GLOBAL
static int probe_value = 7;
#else
static _Thread_local int probe_value = 7;
#endif

int
probe_tls_get(void)
{
#ifdef PROBE_GLOBAL
	return __atomic_load_n(&probe_value, __ATOMIC_SEQ_CST);
#else
	return probe_value;
#endif
}

void
probe_tls_set(int value)
{
#ifdef PROBE_GLOBAL
	__atomic_store_n(&probe_value, value, __ATOMIC_SEQ_CST);
#else
	probe_value = value;
#endif
}
