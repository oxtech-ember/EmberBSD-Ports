/* Exercise the actual S31 CLIC discovery and warm-init source with fake MMIO. */
#include <assert.h>
#include <stdalign.h>
#include <stdint.h>
#include <string.h>
#include SOURCE_FILE

alignas(4) static uint8_t registers[2][0x2000];
static int registration_result;
static int registrations;
static int readonly_mode, readonly_cfg, current_hart;

/* IDF documents the same address as a current-core alias. */
static void *local_address(const void *p)
{
	uintptr_t off = (uintptr_t)p - (uintptr_t)registers[0];
	assert(off < sizeof(registers[0]));
	return registers[current_hart] + off;
}
u32 readl(const void *p) { return *(u32 *)local_address(p); }
void writel(u32 v, void *p)
{
	if (!readonly_cfg)
		*(u32 *)local_address(p) = v;
}
u8 readb(const void *p) { return *(u8 *)local_address(p); }
void writeb(u8 v, void *p)
{
	if (!readonly_mode || v != CLIC_ATTR_S_LEVEL)
		*(u8 *)local_address(p) = v;
}

int fdt_get_node_addr_size(const void *fdt, int node, int index,
    uint64_t *address, uint64_t *size)
{
	(void)fdt; (void)node; (void)index; (void)size;
	*address = (uintptr_t)registers[0];
	return 0;
}

int sbi_irqchip_add_device(struct sbi_irqchip_device *device)
{
	registrations++;
	assert(device->num_hwirq == 48);
	assert(device->target_harts.bits == 3);
	return registration_result;
}

int main(void)
{
	const struct fdt_match *match = &irqchip_clic_match[0];
	memset(registers, 0, sizeof(registers));
	registration_result = -17;
	assert(irqchip_clic_cold_init(0, 0, match) == -17);
	registration_result = 0;
	assert(irqchip_clic_cold_init(0, 0, match) == 0);
	assert(registrations == 2);
	/* Refuse a chip where the measured S-mode configuration is not writable. */
	*(uint32_t *)registers[0] = 3;
	readonly_cfg = 1;
	assert(irqchip_clic_warm_init(&clic_device) == SBI_ENOTSUPP);
	readonly_cfg = 0;
	readonly_mode = 1;
	assert(irqchip_clic_warm_init(&clic_device) == SBI_ENOTSUPP);
	readonly_mode = 0;
	assert(irqchip_clic_warm_init(&clic_device) == 0);
	assert(*(uint32_t *)registers[0] == CLICCFG_S31_VALUE);
	for (int i = 16; i <= 47; i++) {
		assert(registers[0][CLIC_INTATTR_OFF(i)] == CLIC_ATTR_S_LEVEL);
		assert(registers[0][CLIC_INTCTL_OFF(i)] == CLIC_CTL_MAX_PRIO);
		assert(registers[0][CLIC_INTIE_OFF(i)] == 0);
	}
	assert(registers[0][CLIC_INTATTR_OFF(15)] == 0);
	assert(registers[0][CLIC_INTATTR_OFF(48)] == 0);
	uint8_t snapshot[sizeof(registers[0])];
	memcpy(snapshot, registers[0], sizeof(snapshot));
	current_hart = 1;
	*(uint32_t *)registers[1] = 3;
	assert(irqchip_clic_warm_init(&clic_device) == 0);
	assert(memcmp(snapshot, registers[0], sizeof(snapshot)) == 0);
	assert(registers[1][CLIC_INTATTR_OFF(16)] == CLIC_ATTR_S_LEVEL);
	return 0;
}
