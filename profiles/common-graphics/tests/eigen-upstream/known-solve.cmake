# SPDX-License-Identifier: BSD-2-Clause
# Origin: EmberBSD (AI-assisted), numerical oracle for the unchanged example.
execute_process(COMMAND "${EXAMPLE}" RESULT_VARIABLE status OUTPUT_VARIABLE text)
if(NOT status EQUAL 0)
  message(FATAL_ERROR "The upstream solver example failed: ${status}")
endif()
string(FIND "${text}" "The solution is:" marker)
if(marker LESS 0)
  message(FATAL_ERROR "The upstream solver example did not print its solution")
endif()
math(EXPR first "${marker} + 16")
string(SUBSTRING "${text}" ${first} -1 solution)
string(REGEX MATCHALL "[-+]?[0-9]+[.]?[0-9]*([eE][-+]?[0-9]+)?" values "${solution}")
list(LENGTH values count)
if(NOT count EQUAL 3)
  message(FATAL_ERROR "Expected exactly three solution coefficients: ${solution}")
endif()
list(GET values 0 x)
list(GET values 1 y)
list(GET values 2 z)
# x=(-2,1,1) gives the example's b=(3,3,4). Allow its float roundoff.
if(x LESS -2.00001 OR x GREATER -1.99999 OR
   y LESS 0.99999 OR y GREATER 1.00001 OR
   z LESS 0.99999 OR z GREATER 1.00001)
  message(FATAL_ERROR "The known solution is (-2,1,1): ${solution}")
endif()
message("${text}")
