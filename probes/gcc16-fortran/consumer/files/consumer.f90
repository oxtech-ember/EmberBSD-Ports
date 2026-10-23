! SPDX-License-Identifier: BSD-2-Clause
! Origin: EmberBSD; real ISO C binding and runtime formatted I/O.
subroutine ember_fortran_c(value) bind(C)
  use iso_c_binding, only: c_double
  use ieee_arithmetic, only: ieee_is_finite
  implicit none
  real(c_double), intent(out) :: value
  character(len=32) :: buffer
  value = sqrt(144.0_c_double)
  write(buffer, '(F6.1)') value
  if (trim(adjustl(buffer)) /= '12.0') stop 1
  if (.not. ieee_is_finite(value)) stop 2
end subroutine
