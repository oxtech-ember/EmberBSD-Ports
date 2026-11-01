# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted).
# Include after setting EMBERBSD_HOST_PREFIX and before the cross profile.
# Preserve target flags across the host configuration, while native package
# dependencies retain the host flags from that same configuration.
USE_CROSS_COMPILE?=yes

.if !defined(EMBERBSD_HOST_PREFIX) || empty(EMBERBSD_HOST_PREFIX)
.error Set EMBERBSD_HOST_PREFIX before including host-config.mk
.endif
EMBERBSD_HOST_MAKECONF?=${EMBERBSD_HOST_PREFIX}/etc/mk.conf
.if !exists(${EMBERBSD_HOST_MAKECONF})
.error Host make configuration does not exist: ${EMBERBSD_HOST_MAKECONF}
.endif

.for _ember_host_flag in CPPFLAGS CFLAGS CXXFLAGS LDFLAGS
.if defined(${_ember_host_flag})
_EMBER_HOST_CONFIG_${_ember_host_flag}_DEFINED=yes
_EMBER_HOST_CONFIG_${_ember_host_flag}:=${${_ember_host_flag}}
.else
_EMBER_HOST_CONFIG_${_ember_host_flag}_DEFINED=no
.endif
.endfor

.include "${EMBERBSD_HOST_MAKECONF}"

.if ${USE_CROSS_COMPILE:tl} == "yes"
.for _ember_host_flag in CPPFLAGS CFLAGS CXXFLAGS LDFLAGS
.if ${_EMBER_HOST_CONFIG_${_ember_host_flag}_DEFINED} == "yes"
${_ember_host_flag}:=${_EMBER_HOST_CONFIG_${_ember_host_flag}}
.else
.undef ${_ember_host_flag}
.endif
.endfor
.endif
