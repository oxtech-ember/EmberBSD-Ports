/* SPDX-License-Identifier: Apache-2.0 */
/*
 * SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
 * Mosaico ESP32-S31 opt-in LCD diagnostic.
 * Panel sequence adapted from Espressif Mosaico Claw
 * mosaico_boot_splash.c (Apache-2.0), commit
 * 2654a4a9f76f5d7ea108e4dff7ade7b1df4c1c5c.
 */

#include "mosaico_splash_core.h"

#include <string.h>

#define GPIO_BASE               0x20583000U
#define IOMUX_BASE              0x20582000U
#define HP_SYS_CLKRST_BASE      0x20587000U
#define GPSPI2_BASE             0x2038f000U

#define GPIO_OUT_W1TS           (GPIO_BASE + 0x08U)
#define GPIO_OUT_W1TC           (GPIO_BASE + 0x0cU)
#define GPIO_OUT1_W1TS          (GPIO_BASE + 0x14U)
#define GPIO_OUT1_W1TC          (GPIO_BASE + 0x18U)
#define GPIO_ENABLE_W1TS        (GPIO_BASE + 0x38U)
#define GPIO_ENABLE1_W1TS       (GPIO_BASE + 0x44U)
#define GPIO_MATRIX_OUT_BASE    (GPIO_BASE + 0xaf4U)
#define GPIO_MATRIX_OUT_GPIO    256U
#define GPIO_MATRIX_OUT_OE_SEL  BIT(10)
#define IOMUX_MCU_SEL_MASK      (7U << 12)
#define IOMUX_MCU_SEL_GPIO      (1U << 12)
#define GPSPI2_CTRL0            (HP_SYS_CLKRST_BASE + 0x6cU)

#define SPI_CMD                 (GPSPI2_BASE + 0x00U)
#define SPI_CTRL                (GPSPI2_BASE + 0x08U)
#define SPI_CLOCK               (GPSPI2_BASE + 0x0cU)
#define SPI_USER                (GPSPI2_BASE + 0x10U)
#define SPI_USER1               (GPSPI2_BASE + 0x14U)
#define SPI_USER2               (GPSPI2_BASE + 0x18U)
#define SPI_DATA_LEN            (GPSPI2_BASE + 0x1cU)
#define SPI_MISC                (GPSPI2_BASE + 0x20U)
#define SPI_DMA_CONF            (GPSPI2_BASE + 0x30U)
#define SPI_INT_ENA             (GPSPI2_BASE + 0x34U)
#define SPI_SLAVE               (GPSPI2_BASE + 0xe0U)
#define SPI_FIFO                (GPSPI2_BASE + 0x98U)

#define BIT(n)                  (1U << (n))
#define SPI_USR                 BIT(24)
#define SPI_UPDATE              BIT(23)
#define SPI_USER_FWRITE_QUAD    BIT(13)
#define SPI_USER_MOSI           BIT(27)
#define SPI_MISC_CS_KEEP_ACTIVE BIT(30)
#define SPI_CLOCK_DIRECT        BIT(31)
#define SPI_CTRL_FREAD_QUAD     BIT(15)
#define SPI_CTRL_IDLE_HIGH      (BIT(18) | BIT(19) | BIT(20) | BIT(21))

#define SPI_TX_TIMEOUT_MS       100U
#define SPI_FIFO_BYTES          64U
#define LCD_WIDTH               480U
#define LCD_HEIGHT              480U
#define LCD_POWER_GPIO          60U
#define LCD_RESET_GPIO          44U
#define LCD_CS_GPIO             50U
#define LCD_CLK_GPIO            42U
#define LCD_D0_GPIO             36U
#define LCD_D1_GPIO             51U
#define LCD_D2_GPIO             35U
#define LCD_D3_GPIO             9U

struct lcd_init_command {
	uint8_t command;
	uint8_t value;
};

static const struct lcd_init_command lcd_init[] = {
	{ 0xfe, 0x20 }, { 0x19, 0x10 }, { 0x1c, 0xa0 }, { 0xfe, 0x00 },
	{ 0xc4, 0x80 }, { 0x3a, 0x55 }, { 0x53, 0x20 }, { 0x51, 0x66 },
	{ 0x63, 0xff }, { 0x36, 0x00 },
};

static void
write_reg(const struct mosaico_splash_io *io, uintptr_t address,
    uint32_t value)
{
	io->write32(io->cookie, address, value);
}

static uint32_t
read_reg(const struct mosaico_splash_io *io, uintptr_t address)
{
	return io->read32(io->cookie, address);
}

static void
gpio_level(const struct mosaico_splash_io *io, unsigned int gpio,
    bool high)
{
	uintptr_t address;
	unsigned int bit;

	if (gpio < 32U) {
		address = high ? GPIO_OUT_W1TS : GPIO_OUT_W1TC;
		bit = gpio;
	} else {
		address = high ? GPIO_OUT1_W1TS : GPIO_OUT1_W1TC;
		bit = gpio - 32U;
	}
	write_reg(io, address, BIT(bit));
}

static void
gpio_output(const struct mosaico_splash_io *io, unsigned int gpio,
    bool high)
{
	uintptr_t pad = IOMUX_BASE + gpio * 4U;
	uint32_t pad_config = read_reg(io, pad);

	/* Preserve electrical pad settings while selecting the GPIO function. */
	write_reg(io, pad, (pad_config & ~IOMUX_MCU_SEL_MASK) |
	    IOMUX_MCU_SEL_GPIO);
	/* Use the GPIO output register and its enable bit through the matrix. */
	write_reg(io, GPIO_MATRIX_OUT_BASE + gpio * 4U,
	    GPIO_MATRIX_OUT_GPIO | GPIO_MATRIX_OUT_OE_SEL);
	gpio_level(io, gpio, high);
	write_reg(io, gpio < 32U ? GPIO_ENABLE_W1TS : GPIO_ENABLE1_W1TS,
	    BIT(gpio < 32U ? gpio : gpio - 32U));
}

static void
route_spi_output(const struct mosaico_splash_io *io, unsigned int gpio,
    unsigned int signal)
{
	uintptr_t pad = IOMUX_BASE + gpio * 4U;
	uint32_t pad_config = read_reg(io, pad);

	write_reg(io, pad, (pad_config & ~IOMUX_MCU_SEL_MASK) |
	    IOMUX_MCU_SEL_GPIO);
	/* Keep peripheral-controlled OE_SEL clear for SPI signals. */
	write_reg(io, GPIO_MATRIX_OUT_BASE + gpio * 4U, signal);
	write_reg(io, gpio < 32U ? GPIO_ENABLE_W1TS : GPIO_ENABLE1_W1TS,
	    BIT(gpio < 32U ? gpio : gpio - 32U));
}

static int
wait_for_spi(const struct mosaico_splash_io *io)
{
	uint32_t start = io->time_ms(io->cookie);

	while ((read_reg(io, SPI_CMD) & (SPI_USR | SPI_UPDATE)) != 0) {
		if ((uint32_t)(io->time_ms(io->cookie) - start) >=
		    SPI_TX_TIMEOUT_MS)
			return -1;
	}
	return 0;
}

static int
spi_tx(const struct mosaico_splash_io *io, const uint8_t *data,
    size_t length, unsigned int lines, bool keep_cs)
{
	size_t i;
	uint32_t user;

	if (data == NULL || length == 0 || length > SPI_FIFO_BYTES ||
	    (lines != 1 && lines != 4))
		return -1;
	if (wait_for_spi(io) != 0)
		return -1;

	/* FIFO words are little-endian on the S31 RISC-V core. */
	for (i = 0; i < length; i += 4U) {
		uint32_t word = 0;
		size_t j;

		for (j = 0; j < 4U && i + j < length; j++)
			word |= (uint32_t)data[i + j] << (j * 8U);
		write_reg(io, SPI_FIFO + (i / 4U) * 4U, word);
	}

	write_reg(io, SPI_DATA_LEN, (uint32_t)(length * 8U - 1U));
	write_reg(io, SPI_USER1, 0);
	write_reg(io, SPI_USER2, 0);
	write_reg(io, SPI_CTRL,
	    SPI_CTRL_IDLE_HIGH | (lines == 4 ? SPI_CTRL_FREAD_QUAD : 0));
	user = SPI_USER_MOSI;
	if (lines == 4)
		user |= SPI_USER_FWRITE_QUAD;
	write_reg(io, SPI_USER, user);
	write_reg(io, SPI_MISC, 0x3eU |
	    (keep_cs ? SPI_MISC_CS_KEEP_ACTIVE : 0));
	write_reg(io, SPI_CMD, SPI_UPDATE);
	if (wait_for_spi(io) != 0)
		return -1;
	write_reg(io, SPI_CMD, SPI_USR);
	return wait_for_spi(io);
}

static int
lcd_command(const struct mosaico_splash_io *io, uint8_t command,
    const uint8_t *parameter, size_t parameter_length)
{
	uint8_t packet[8] = { 0x02, 0x00, command, 0x00 };

	if (parameter_length > sizeof(packet) - 4U ||
	    (parameter_length != 0 && parameter == NULL))
		return -1;
	if (parameter_length != 0)
		memcpy(&packet[4], parameter, parameter_length);
	return spi_tx(io, packet, 4U + parameter_length, 1, false);
}

static int
lcd_set_window(const struct mosaico_splash_io *io)
{
	static const uint8_t columns[] = { 0x00, 0x00, 0x01, 0xdf };
	static const uint8_t rows[] = { 0x00, 0x00, 0x01, 0xdf };
	int error;

	error = lcd_command(io, 0x2a, columns, sizeof(columns));
	if (error != 0)
		return error;
	return lcd_command(io, 0x2b, rows, sizeof(rows));
}

static int
lcd_write_solid(const struct mosaico_splash_io *io, uint16_t rgb565)
{
	uint8_t prefix[] = { 0x32, 0x00, 0x2c, 0x00 };
	uint8_t pixels[SPI_FIFO_BYTES];
	unsigned int chunk, chunks = LCD_WIDTH * LCD_HEIGHT * 2U /
	    SPI_FIFO_BYTES;

	if (spi_tx(io, prefix, sizeof(prefix), 1, true) != 0)
		return -1;
	for (chunk = 0; chunk < sizeof(pixels); chunk += 2U) {
		pixels[chunk] = (uint8_t)(rgb565 >> 8);
		pixels[chunk + 1U] = (uint8_t)rgb565;
	}
	for (chunk = 0; chunk < chunks; chunk++) {
		if (spi_tx(io, pixels, sizeof(pixels), 4,
		    chunk + 1U < chunks) != 0)
			return -1;
	}
	return 0;
}

static void
spi_init(const struct mosaico_splash_io *io)
{
	uint32_t control;

	control = read_reg(io, GPSPI2_CTRL0);
	write_reg(io, GPSPI2_CTRL0, control | BIT(0) | BIT(1));
	write_reg(io, GPSPI2_CTRL0, control | BIT(0) | BIT(1) | BIT(2));
	write_reg(io, GPSPI2_CTRL0, (control | BIT(0) | BIT(1) | BIT(6) |
	    BIT(23)) & ~(BIT(2) | (3U << 4) | (0xffU << 7) |
	    (0xffU << 15)));

	route_spi_output(io, LCD_CLK_GPIO, 53);
	route_spi_output(io, LCD_D0_GPIO, 55);
	route_spi_output(io, LCD_D1_GPIO, 54);
	route_spi_output(io, LCD_D2_GPIO, 57);
	route_spi_output(io, LCD_D3_GPIO, 56);
	route_spi_output(io, LCD_CS_GPIO, 62);

	write_reg(io, SPI_CLOCK, SPI_CLOCK_DIRECT);
	write_reg(io, SPI_CTRL, SPI_CTRL_IDLE_HIGH);
	write_reg(io, SPI_USER1, 0);
	write_reg(io, SPI_USER2, 0);
	write_reg(io, SPI_USER, 0);
	write_reg(io, SPI_MISC, 0x3eU);
	write_reg(io, SPI_SLAVE, 0);
	write_reg(io, SPI_DMA_CONF, 0);
	write_reg(io, SPI_INT_ENA, 0);
}

int
mosaico_splash_run(const struct mosaico_splash_io *io, uint16_t rgb565)
{
	unsigned int i;
	int error;

	if (io == NULL || io->read32 == NULL || io->write32 == NULL ||
	    io->time_ms == NULL || io->delay_us == NULL)
		return -1;

	/* Claw powers the panel by pulling active-low GPIO60 down. */
	gpio_output(io, LCD_POWER_GPIO, false);
	gpio_output(io, LCD_RESET_GPIO, false);
	io->delay_us(io->cookie, 10000);
	gpio_level(io, LCD_RESET_GPIO, true);
	io->delay_us(io->cookie, 150000);
	spi_init(io);

	error = lcd_command(io, 0x11, NULL, 0);
	if (error != 0)
		return error;
	io->delay_us(io->cookie, 60000);
	for (i = 0; i < sizeof(lcd_init) / sizeof(lcd_init[0]); i++) {
		error = lcd_command(io, lcd_init[i].command,
		    &lcd_init[i].value, 1);
		if (error != 0)
			return error;
	}
	if (lcd_set_window(io) != 0 || lcd_write_solid(io, rgb565) != 0)
		return -1;
	return lcd_command(io, 0x29, NULL, 0);
}
