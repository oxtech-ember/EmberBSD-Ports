// SPDX-License-Identifier: GPL-2.0+ AND MIT
/*
 * MPLL and analog I2C sequences adapted from esp-hal esp32s31/clocks.rs and
 * esp32s31/regi2c.rs, copyright 2021 esp-rs, MIT license. See
 * emberbsd-licenses/esp-hal-MIT. Source revision:
 * 41b881629e88acdf0011963eae0ffa8074c9f2b7.
 * Hardware sequence also cross-checked against ESP-IDF revision
 * d445e947156f276dfe0db5804e4edf6ae90fe6fb.
 *
 * ESP32-S31 SPL clock-tree bring-up: MPLL (EMAC ref path), CPU→CPLL
 * (320 MHz), and the systimer peripheral clock. First-stage bring-up, so it
 * lives in the SPL (which runs from uncached HP-RAM), not in the OpenSBI
 * runtime. Ported from the OpenSBI port's esp32s31_generic.c; register/ROM
 * addresses are chip constants.
 */

#include <hang.h>
#include <stdio.h>
#include <asm/io.h>
#include <linux/bitops.h>
#include <linux/types.h>

#include "spl_clk.h"
#include "spl_poll.h"

#define ESP32S31_PMU_BASE                 0x20704000U
#define ESP32S31_LP_AONCLKRST_BASE        0x20701000U
#define ESP32S31_HP_ALIVE_SYS_BASE        0x20589000U
#define ESP32S31_HP_SYS_CLKRST_BASE       0x20587000U
#define ESP32S31_MODEM_LPCON_BASE         0x2010F000U
#define ESP32S31_MODEM_SYSCON_BASE        0x20109C00U

/* Read-modify-write one register field (clear `mask`, OR in `val`). */
static void reg_set_field(void *reg, u32 mask, u32 val)
{
	writel((readl(reg) & ~mask) | val, reg);
}

/*
 * Bring up the MPLL (500 MHz) feeding MSPI/PSRAM and the EMAC reference
 * clock. One initialization runs before the PSRAM controller and configures
 * the analog I2C master and MPLL before calibration.
 */
#define PMU_IMM_HP_CK_POWER_1_OFF         0xF4U
#define PMU_HP_ACTIVE_HP_CK_POWER_OFF     0x1CU
#define HP_ALIVE_SYS_HP_CLK_CTRL_OFF      0x00U
#define LP_AONCLKRST_MSPI_DIV_OFF         0x54U
#define HP_SYS_CLKRST_ANA_PLL_CTRL0_OFF   0x174U
#define HP_SYS_CLKRST_MODEM_CTRL0_OFF     0x40U
#define MODEM_LPCON_CLK_CONF_OFF          0x18U
#define MODEM_LPCON_CLK_CONF_FORCE_ON_OFF 0x1CU
#define MODEM_SYSCON_CLK_CONF_OFF         0x04U

#define PMU_TIE_HIGH_GLOBAL_MPLL_ICG      BIT(22)
#define PMU_TIE_HIGH_XPD_MPLL_I2C         BIT(26)
#define PMU_TIE_HIGH_XPD_MPLL             BIT(30)
#define PMU_HP_ACTIVE_XPD_MPLL_I2C        BIT(26)
#define PMU_HP_ACTIVE_XPD_MPLL            BIT(30)
#define PMU_TIE_HIGH_CPLL_BITS            (BIT(19) | BIT(23) | BIT(27))
#define PMU_HP_ACTIVE_ALL_PLL_XPD         0x5dc00000U
#define HP_ALIVE_SYS_HP_MPLL_500M_CLK_EN  BIT(31)
#define MSPI_FB_DIV_MASK                  (0x1FU << 3)
#define MSPI_FB_DIV_500MHZ                (24U << 3)
#define MSPI_CAL_END                      BIT(8)
#define MSPI_CAL_STOP                     BIT(9)
#define HP_SYS_CLKRST_MODEM_CLK_EN        BIT(0)
#define MODEM_LPCON_CLK_I2C_MST_EN        BIT(2)
#define MODEM_LPCON_CLK_I2C_MST_FO        BIT(2)
#define MODEM_SYSCON_CLK_I2C_MST_SEL_160M BIT(12)

#define S31_ANA_I2C_BASE                  0x2010f800U
#define S31_ANA_I2C_CONF1                 (S31_ANA_I2C_BASE + 0x1cU)
#define S31_ANA_I2C_CONF2                 (S31_ANA_I2C_BASE + 0x20U)
#define S31_ANA_I2C_MPLL_SELECT           BIT(12)
#define S31_ANA_I2C_BUSY                  BIT(25)
#define S31_ANA_I2C_WRITE                 BIT(24)
#define S31_ANA_I2C_DATA_SHIFT            16
#define S31_ANA_I2C_ADDR_SHIFT            8
#define S31_ANA_I2C_MPLL                  0x0bU

/* Adapted from esp-hal's regi2c_enable_block (regi2c.rs:228-274).
 * This board path uses only the MPLL slave; clocks are enabled by the caller.
 */
static void *
s31_mpll_i2c_controller(void)
{
	void *conf1 = (void *)S31_ANA_I2C_CONF1;
	const void *conf2 = (const void *)S31_ANA_I2C_CONF2;
	u32 sel;

	sel = (readl(conf2) & (S31_ANA_I2C_MPLL_SELECT << 4)) ? 0 : 1;
	writel(~(S31_ANA_I2C_MPLL_SELECT << 2) & 0x00ffffffU, conf1);
	return (void *)(unsigned long)(S31_ANA_I2C_BASE + sel * 4);
}

/* regi2c_read (regi2c.rs:294-311), with bounded idle waits. */
static int
s31_mpll_i2c_read(u32 reg, u32 *value)
{
	void *ctrl = s31_mpll_i2c_controller();
	u32 command = S31_ANA_I2C_MPLL | (reg << S31_ANA_I2C_ADDR_SHIFT);

	if (!s31_poll_register(ctrl, S31_ANA_I2C_BUSY, 0))
		return -1;
	writel(command, ctrl);
	if (!s31_poll_register(ctrl, S31_ANA_I2C_BUSY, 0))
		return -1;
	*value = (readl(ctrl) >> S31_ANA_I2C_DATA_SHIFT) & 0xffU;
	return 0;
}

/* regi2c_write (regi2c.rs:313-328), with bounded idle waits. */
static int
s31_mpll_i2c_write(u32 reg, u32 value)
{
	void *ctrl = s31_mpll_i2c_controller();
	u32 command = S31_ANA_I2C_MPLL | (reg << S31_ANA_I2C_ADDR_SHIFT) |
	    S31_ANA_I2C_WRITE | ((value & 0xffU) << S31_ANA_I2C_DATA_SHIFT);

	if (!s31_poll_register(ctrl, S31_ANA_I2C_BUSY, 0))
		return -1;
	writel(command, ctrl);
	if (!s31_poll_register(ctrl, S31_ANA_I2C_BUSY, 0))
		return -1;
	return 0;
}

/* RegI2cField::write_field (rom/regi2c.rs:78-83). */
static int
s31_mpll_i2c_update(u32 reg, u32 mask, u32 value)
{
	u32 old;

	if (s31_mpll_i2c_read(reg, &old))
		return -1;
	return s31_mpll_i2c_write(reg, (old & ~mask) | (value & mask));
}

int
s31_spl_mpll_enable(void)
{
	void *pmu_imm    = (void *)(ESP32S31_PMU_BASE + PMU_IMM_HP_CK_POWER_1_OFF);
	void *pmu_active = (void *)(ESP32S31_PMU_BASE + PMU_HP_ACTIVE_HP_CK_POWER_OFF);
	void *hp_alive   = (void *)(ESP32S31_HP_ALIVE_SYS_BASE + HP_ALIVE_SYS_HP_CLK_CTRL_OFF);
	void *mspi_div   = (void *)(ESP32S31_LP_AONCLKRST_BASE + LP_AONCLKRST_MSPI_DIV_OFF);
	void *ana_pll    = (void *)(ESP32S31_HP_SYS_CLKRST_BASE + HP_SYS_CLKRST_ANA_PLL_CTRL0_OFF);
	void *modem_bus  = (void *)(ESP32S31_HP_SYS_CLKRST_BASE + HP_SYS_CLKRST_MODEM_CTRL0_OFF);
	void *lpcon_clk  = (void *)(ESP32S31_MODEM_LPCON_BASE + MODEM_LPCON_CLK_CONF_OFF);
	void *lpcon_fo   = (void *)(ESP32S31_MODEM_LPCON_BASE + MODEM_LPCON_CLK_CONF_FORCE_ON_OFF);
	void *syscon_clk = (void *)(ESP32S31_MODEM_SYSCON_BASE + MODEM_SYSCON_CLK_CONF_OFF);
	u32 v;
	bool ready;

	/* MPLL calibration uses the analog I2C master (MODEM domain). Bring up
	 * its bus + clocks first, mirroring IDF bootloader_hardware_init().
	 */
	v = readl(modem_bus);
	writel(v | HP_SYS_CLKRST_MODEM_CLK_EN, modem_bus);
	v = readl(lpcon_clk);
	writel(v | MODEM_LPCON_CLK_I2C_MST_EN, lpcon_clk);
	v = readl(lpcon_fo);
	writel(v | MODEM_LPCON_CLK_I2C_MST_FO, lpcon_fo);
	v = readl(syscon_clk);
	writel(v | MODEM_SYSCON_CLK_I2C_MST_SEL_160M, syscon_clk);

	/* Power on the MPLL analog core + I2C interface, ungate its clock. */
	v = readl(pmu_imm);
	writel(v | PMU_TIE_HIGH_CPLL_BITS | PMU_TIE_HIGH_GLOBAL_MPLL_ICG |
		   PMU_TIE_HIGH_XPD_MPLL_I2C |
		   PMU_TIE_HIGH_XPD_MPLL, pmu_imm);

	v = readl(pmu_active);
	writel(v | PMU_HP_ACTIVE_ALL_PLL_XPD, pmu_active);

	v = readl(hp_alive);
	writel(v | HP_ALIVE_SYS_HP_MPLL_500M_CLK_EN, hp_alive);

	/* Configure analog capacitance and reference before CAL_START. */
	if (s31_mpll_i2c_update(1, 0x03, 0x03) ||
	    s31_mpll_i2c_update(1, 0x04, 0x04))
		goto i2c_timeout;
	reg_set_field(mspi_div, MSPI_FB_DIV_MASK, 9U << 3);
	if (s31_mpll_i2c_update(3, 0x30, 0x30) ||
	    s31_mpll_i2c_update(1, 0x04, 0))
		goto i2c_timeout;

	v = readl(ana_pll);
	writel(v & ~MSPI_CAL_STOP, ana_pll);
	reg_set_field(mspi_div, MSPI_FB_DIV_MASK, MSPI_FB_DIV_500MHZ);
	ready = s31_poll_register(ana_pll, MSPI_CAL_END, MSPI_CAL_END);
	v = readl(ana_pll);
	writel(v | MSPI_CAL_STOP, ana_pll);
	if (!ready) {
		puts("spl: MPLL calibration timeout\n");
		return -1;
	}
	return 0;

i2c_timeout:
	puts("spl: MPLL analog I2C timeout\n");
	return -1;
}

/*
 * Switch CPU from XTAL (40 MHz) to CPLL (320 MHz): CPU=320, MEM=160, SYS~107,
 * APB~53 MHz. The CLINT MTIME is CPU-clocked, so it moves to 320 MHz too —
 * the dts timebase-frequency (320M) and esp_systimer .timer_freq follow.
 */
#define HP_CLKRST_SOC_CLK_SEL             0x00U
#define HP_CLKRST_CPU_FREQ_CTRL0          0x04U
#define HP_CLKRST_MEM_FREQ_CTRL0          0x08U
#define HP_CLKRST_SYS_FREQ_CTRL0          0x0CU
#define HP_CLKRST_APB_FREQ_CTRL0          0x10U
#define HP_CLKRST_ROOT_CLK_CTRL0          0x14U
#define LP_AONCLKRST_CPLL_DIV             0x4CU	/* b[3:0] ref_div, b[11:4] fb_div */
#define ANA_PLL_CPU_CAL_END               BIT(2)	/* RO */
#define ANA_PLL_CPU_CAL_STOP              BIT(3)

void s31_spl_cpu_switch_to_cpll(void)
{
	char *hc = (char *)ESP32S31_HP_SYS_CLKRST_BASE;
	void *cpll_div = (void *)(ESP32S31_LP_AONCLKRST_BASE + LP_AONCLKRST_CPLL_DIV);
	void *cal = (void *)(ESP32S31_HP_SYS_CLKRST_BASE + HP_SYS_CLKRST_ANA_PLL_CTRL0_OFF);
	int guard;

	/* Program the CPLL to 320 MHz (40 MHz XTAL * fb_div/ref_div = 40*8/1).
	 * The ROM leaves it at fb_div=15/ref_div=2 = 300 MHz, so without this the
	 * CPU runs at 300, not 320. CPU is still on XTAL here, so the idle CPLL
	 * can be re-tuned + recalibrated safely.
	 */
	reg_set_field(cpll_div, 0xFU, 1U);		/* ref_div = 1 */
	reg_set_field(cpll_div, 0xFF0U, 8U << 4);	/* fb_div = 8 */
	writel(readl(cal) & ~ANA_PLL_CPU_CAL_STOP, cal);	/* start calibration */
	for (guard = 1000000; !(readl(cal) & ANA_PLL_CPU_CAL_END) && guard; guard--)
		;
	if (!guard) {
		puts("SPL: CPLL calibration timed out\n");
		hang();
	}
	writel(readl(cal) | ANA_PLL_CPU_CAL_STOP, cal);		/* stop calibration */

	/* Set dividers BEFORE switching source (IDF sequence). */
	reg_set_field(hc + HP_CLKRST_CPU_FREQ_CTRL0, 0xFFU, 0);   /* /1 */
	reg_set_field(hc + HP_CLKRST_MEM_FREQ_CTRL0, 0x1U,  1);   /* /2 */
	reg_set_field(hc + HP_CLKRST_SYS_FREQ_CTRL0, 0xFFU, 2);   /* /3 */
	reg_set_field(hc + HP_CLKRST_APB_FREQ_CTRL0, 0xFFU, 1);   /* /2 */

	/* Switch XTAL -> CPLL (SOC_CLK_SEL = 1 = CPLL). */
	reg_set_field(hc + HP_CLKRST_SOC_CLK_SEL, 0x3U, 1U);

	/* Commit (SOC_CLK_UPDATE) and wait for self-clear (bounded). */
	writel(readl(hc + HP_CLKRST_ROOT_CLK_CTRL0) | BIT(0),
	       hc + HP_CLKRST_ROOT_CLK_CTRL0);
	for (guard = 1000000;
	     (readl(hc + HP_CLKRST_ROOT_CLK_CTRL0) & BIT(0)) && guard; guard--)
		;
	if (!guard) {
		puts("SPL: CPLL clock switch timed out\n");
		hang();
	}
}

/*
 * Bring up the systimer peripheral so Linux can use it as its always-on
 * clocksource/clockevent. XTAL-fed (40 MHz / 2.5 = 16 MHz), independent of
 * CPU_CLK, free-running through WFI (unlike the CPU-clocked CLINT MTIME).
 * HP_SYS_CLKRST systimer_ctrl0 @ +0x120; SYSTIMER CONF @ base.
 */
#define ESP32S31_SYSTIMER_BASE            0x20399000U
#define HP_CLKRST_SYSTIMER_CTRL0          0x120U

void s31_spl_systimer_clk_init(void)
{
	void *clk = (void *)(ESP32S31_HP_SYS_CLKRST_BASE + HP_CLKRST_SYSTIMER_CTRL0);
	void *conf = (void *)ESP32S31_SYSTIMER_BASE;

	reg_set_field(clk, BIT(3), 0);			/* clk_src_sel = XTAL */
	writel(readl(clk) | BIT(0) | BIT(4), clk);	/* apb_clk_en + clk_en */
	writel(readl(clk) | BIT(1), clk);		/* pulse reset */
	writel(readl(clk) & ~BIT(1), clk);
	/* UNIT0 free-running: work_en set, not stalled by either core. */
	writel((readl(conf) | BIT(30)) & ~(BIT(27) | BIT(28)), conf);
}
