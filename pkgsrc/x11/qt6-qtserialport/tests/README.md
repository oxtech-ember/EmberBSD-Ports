# NetBSD serial discovery

The recipe selects a NetBSD backend that reads device properties through
`drvctl` and libprop. Enumeration never opens a serial port. It keeps
dial-out device aliases and symbolic links by matching device numbers.
Attached USB serial ports carry their vendor, product and serial identifiers.
If `drvctl` is inaccessible, named serial nodes remain available without USB
metadata. Static non-USB nodes are listed without claiming attached hardware.

Build the two C++ checks with the selected native compiler and Qt Core and
SerialPort libraries. Compile with `-fPIC` where Qt requires reduced relocations.
Pass the patched `src/serialport` directory as an include path for
`netbsd-device-names.cpp`. This check exercises the production name classifier,
including native, multiport and USB families from NetBSD MAKEDEV.

Run `netbsd-enumeration` with no arguments for a generic list check. To check a
known attached USB device, pass its path, hexadecimal vendor and product IDs,
and serial number. The check rejects unrelated devices and verifies metadata:

```sh
netbsd-enumeration /dev/dtyU0 VENDOR PRODUCT SERIAL
```

Repeat the check for an existing character alias and a temporary symbolic link
to the same serial device. Remove only the alias created for this check.
After unplug, an accessible `drvctl` must exclude the detached USB unit. After
replug, verify the new unit and its stable alias. Use an application runtime
check to confirm that the selected alias can still be opened.

The enumeration check does not prove UART traffic, radio reception or physical
hot-unplug recovery. Those need an attached device and its remote endpoint.
