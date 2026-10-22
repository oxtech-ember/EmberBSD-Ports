#!/usr/bin/env python3.15
# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted). Read-only resource checks; no guest execution.
from vm import integer, ram_mib

checks = 0
assert ram_mib() == 1024
checks += 1
for value in [1024, 4096, 8192]:
    for item in [value, str(value)]:
        assert ram_mib(item) == value
        checks += 1
for value in [None, True, False, 1024.0, 1023, 8193, -1, 0, '', ' ', '1023', '8193', '4096.0', '1_024', '+1024', '-1024', ' 1024', '1024\n', '4096m']:
    try:
        ram_mib(value)
    except ValueError as error:
        assert str(error) == 'RAM must be an integer from 1024 to 8192 MiB'
        checks += 1
    else:
        raise AssertionError(f'Invalid RAM accepted: {value!r}')
for value in [1, 4, 8, '1', '4', '8']:
    assert integer(value, 1, 8, 'virtual CPUs') == int(value)
    checks += 1
for value in [0, 9, None, True, '4.0', ' 4', '4\n']:
    try:
        integer(value, 1, 8, 'virtual CPUs')
    except ValueError:
        checks += 1
    else:
        raise AssertionError(f'Invalid vCPU count accepted: {value!r}')
print(f'PASS: {checks} resource checks; no filesystem mutation or guest execution')
