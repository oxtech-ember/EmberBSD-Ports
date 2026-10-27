# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD contributors (AI-assisted).
# The fixture exercises option selection only; no compiler is enabled or invoked.
function(check_cxx_compiler_flag FLAG RESULT)
    set(${RESULT} TRUE PARENT_SCOPE)
endfunction()
