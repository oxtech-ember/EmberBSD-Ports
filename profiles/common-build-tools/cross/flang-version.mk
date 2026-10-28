# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted); version of the selected build-host Flang.
# Include only after checking that EMBERBSD_FLANG names an existing driver.
_EMBER_FLANG_VERSION!=set -- $$(${EMBERBSD_FLANG:Q} --version); echo "$$3"
_EMBER_FLANG_MAJOR=${_EMBER_FLANG_VERSION:C/\..*//}
