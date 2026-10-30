# SPDX-License-Identifier: BSD-2-Clause
# Copyright (c) 2026 EmberBSD contributors.
# Origin: EmberBSD (AI-assisted).
"""Compatibility entry points for the shared freestanding WASI producer."""
import freestanding


def build(owner, args):
    return freestanding.build(owner, args, 'wasm32-wasip1')


def verify(owner, args):
    return freestanding.verify(owner, args, 'wasm32-wasip1')
