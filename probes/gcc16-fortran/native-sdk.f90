program native_sdk_probe
  implicit none
  integer :: value
  value = 42
  if (value /= 42) error stop 1
  print *, value
end program native_sdk_probe
