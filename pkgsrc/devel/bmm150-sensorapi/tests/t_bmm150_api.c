/*
 * SPDX-License-Identifier: BSD-2-Clause
 */

#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "bmm150.h"

struct fake_bmm150 {
	uint8_t regs[256];
	int fail_read_reg;
	int fail_write_reg;
};

static int8_t
fake_read(uint8_t reg, uint8_t *data, uint32_t len, void *cookie)
{
	struct fake_bmm150 *fake = cookie;

	if (fake->fail_read_reg == reg || len > sizeof(fake->regs) - reg)
		return -1;
	memcpy(data, &fake->regs[reg], len);
	return 0;
}

static int8_t
fake_write(uint8_t reg, const uint8_t *data, uint32_t len, void *cookie)
{
	struct fake_bmm150 *fake = cookie;

	if (fake->fail_write_reg == reg || len > sizeof(fake->regs) - reg)
		return -1;
	memcpy(&fake->regs[reg], data, len);
	return 0;
}

static void
fake_delay(uint32_t usec, void *cookie)
{
	(void)usec;
	(void)cookie;
}

static void
fake_init(struct bmm150_dev *dev, struct fake_bmm150 *fake)
{
	memset(fake, 0, sizeof(*fake));
	fake->fail_read_reg = -1;
	fake->fail_write_reg = -1;
	fake->regs[BMM150_REG_CHIP_ID] = BMM150_CHIP_ID;
	memset(dev, 0, sizeof(*dev));
	dev->intf = BMM150_I2C_INTF;
	dev->intf_ptr = fake;
	dev->read = fake_read;
	dev->write = fake_write;
	dev->delay_us = fake_delay;
}

int
main(void)
{
	struct bmm150_dev dev;
	struct fake_bmm150 fake;
	struct bmm150_mag_data mag;
	uint8_t raw_mag[8] = { 0x40, 31, 0x60, 0xf0, 0x60, 9, 0xd0, 7 };
	uint8_t value;

	fake_init(&dev, &fake);
	assert(bmm150_init(&dev) == BMM150_OK);
	assert(dev.chip_id == BMM150_CHIP_ID);

	fake_init(&dev, &fake);
	fake.fail_read_reg = BMM150_REG_POWER_CONTROL;
	assert(bmm150_init(&dev) == BMM150_E_COM_FAIL);

	fake_init(&dev, &fake);
	fake.fail_write_reg = BMM150_REG_POWER_CONTROL;
	assert(bmm150_init(&dev) == BMM150_E_COM_FAIL);

	fake_init(&dev, &fake);
	assert(bmm150_get_regs(BMM150_REG_CHIP_ID, &value, 1, &dev) ==
	    BMM150_OK);
	fake.fail_read_reg = BMM150_REG_CHIP_ID;
	assert(bmm150_get_regs(BMM150_REG_CHIP_ID, &value, 1, &dev) ==
	    BMM150_E_COM_FAIL);

	dev.trim_data.dig_x1 = -5;
	dev.trim_data.dig_y1 = 2;
	dev.trim_data.dig_x2 = 1;
	dev.trim_data.dig_y2 = 2;
	dev.trim_data.dig_z1 = 30000;
	dev.trim_data.dig_z2 = -10000;
	dev.trim_data.dig_z3 = 2;
	dev.trim_data.dig_z4 = 1000;
	dev.trim_data.dig_xy1 = 40;
	dev.trim_data.dig_xy2 = -1;
	dev.trim_data.dig_xyz1 = 30000;
	assert(bmm150_aux_mag_data(raw_mag, &mag, &dev) == BMM150_OK);
	assert(mag.x != BMM150_OVERFLOW_OUTPUT);
	assert(mag.y != BMM150_OVERFLOW_OUTPUT);
	assert(mag.z != BMM150_OVERFLOW_OUTPUT);

	return 0;
}
