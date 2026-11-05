# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); version of the selected build-host Flang.
# Include only after checking that _EMBER_FLANG_DRIVER names an existing driver.
_EMBER_FLANG_VERSION!=set -- $$(${_EMBER_FLANG_DRIVER:Q} --version); echo "$$3"
_EMBER_FLANG_MAJOR=${_EMBER_FLANG_VERSION:C/\..*//}
