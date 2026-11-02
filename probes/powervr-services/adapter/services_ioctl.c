/* Origin: EmberBSD; AI-assisted PowerVR Services ABI experiment. */
/* SPDX-License-Identifier: BSD-2-Clause */

#include <errno.h>
#include <string.h>

#include "bridge_drm.h"
#include "errno_abi.h"
#include "services_ioctl.h"

static int
finish(int error, int saved_errno)
{
	if (error != 0 && pvr_abi_errno_set_native(error) != 0)
		(void)pvr_abi_errno_set_native(EIO);
	errno = saved_errno;
	return error == 0 ? 0 : -1;
}

static int
valid_range(uint64_t address, uint32_t length)
{
	return length == 0 ||
	    (address != 0 && address <= UINT64_MAX - (length - 1));
}

int
pvr_abi_services_ioctl(const struct pvr_abi_services *services,
    uint64_t request, uint64_t argument)
{
	const struct pvr_abi_services_command *command = NULL, *entry;
	struct pvr_abi_bridge_command decoded;
	unsigned char envelope[PVR_ABI_DRM_BYTES];
	size_t i;
	int error, saved_errno = errno;

	if (request != PVR_ABI_DRM_REQUEST)
		return finish(ENOTTY, saved_errno);
	if (services == NULL)
		return finish(EINVAL, saved_errno);
	if (services->connection == NULL)
		return finish(EBADF, saved_errno);
	if (services->read_memory == NULL || services->write_memory == NULL ||
	    (services->command_count != 0 && services->commands == NULL))
		return finish(EINVAL, saved_errno);
	if (!valid_range(argument, PVR_ABI_DRM_BYTES))
		return finish(EFAULT, saved_errno);
	error = services->read_memory(services->memory_cookie, argument,
	    envelope, sizeof(envelope));
	if (error != 0)
		return finish(error, saved_errno);
	if (pvr_abi_bridge_drm_decode(request, envelope, sizeof(envelope),
	    &decoded) != PVR_ABI_BRIDGE_OK)
		return finish(EINVAL, saved_errno);
	for (i = 0; i < services->command_count; i++) {
		entry = &services->commands[i];
		if (entry->bridge_id != decoded.bridge_id ||
		    entry->function_id != decoded.function_id)
			continue;
		if (command != NULL)
			return finish(EINVAL, saved_errno);
		command = entry;
	}
	if (command == NULL)
		return finish(ENOTTY, saved_errno);
	if (command->invoke == NULL ||
	    command->input_size != decoded.input_size ||
	    command->output_size != decoded.output_size ||
	    command->input_size > services->input_capacity ||
	    command->output_size > services->output_capacity ||
	    (command->input_size != 0 && services->input == NULL) ||
	    (command->output_size != 0 && services->output == NULL))
		return finish(EINVAL, saved_errno);
	if (!valid_range(decoded.input_address, decoded.input_size) ||
	    !valid_range(decoded.output_address, decoded.output_size))
		return finish(EFAULT, saved_errno);
	if (decoded.input_size != 0) {
		error = services->read_memory(services->memory_cookie,
		    decoded.input_address, services->input, decoded.input_size);
		if (error != 0)
			return finish(error, saved_errno);
	}
	if (decoded.output_size != 0)
		memset(services->output, 0, decoded.output_size);
	error = command->invoke(services->connection,
	    decoded.input_size != 0 ? services->input : NULL,
	    decoded.output_size != 0 ? services->output : NULL);
	if (error != 0)
		return finish(error, saved_errno);
	if (decoded.output_size != 0) {
		error = services->write_memory(services->memory_cookie,
		    decoded.output_address, services->output, decoded.output_size);
		if (error != 0)
			return finish(error, saved_errno);
	}
	return finish(0, saved_errno);
}
