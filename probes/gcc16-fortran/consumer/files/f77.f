C     SPDX-License-Identifier: BSD-2-Clause
C     Origin: EmberBSD; fixed-form runtime consumer.
      subroutine ember_fortran_f77(value)
      integer value
      character*16 buffer
      value = 42
      write(buffer, '(I4)') value
      if (buffer.ne.'  42') stop 3
      end
