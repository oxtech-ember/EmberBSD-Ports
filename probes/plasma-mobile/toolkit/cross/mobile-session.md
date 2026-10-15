# Plasma Mobile 6.8.0 session entry points

All packages install into the common cross sysroot. Nothing here was
accepted on a board yet; the acceptance targets are the VirGL VM first,
then CM5 after recovery, then Zero 3W once the PowerVR stack lands.

## Upstream launcher

`startplasmamobile` (plasma6-plasma-mobile) exports the mobile
environment (`PLASMA_PLATFORM=phone:handset`,
`PLASMA_DEFAULT_SHELL=org.kde.plasma.mobileshell`) and runs
`startplasma-wayland` from plasma-workspace. This is the full-shell
session: plasmashell loads the mobileshell package.

## Constrained-shell variant

`plasma-nano` provides the compact shell package. On devices where the
full shell is too heavy, start kwin_wayland and run the nano shell
instead of plasmashell; the breeze.mobile look-and-feel from
plasma-mobile selects the phone layout.

## On-screen keyboard

Qt Virtual Keyboard 6.12.0 is cross-built (inputmethod/qt6-qtvirtualkeyboard).
Export `QT_IM_MODULE=qtvirtualkeyboard` for Qt applications. The
upstream Maliit stack is not ported; KWin's input-method protocol
integration is a later track.

## Known boundaries

- Screen recording quick setting is absent: KPipeWire is not ported
  (its crate needs PipeWire; PipeWire needs timerfd/eventfd on NetBSD).
- NetworkManager and ModemManager daemons do not exist on NetBSD. The
  Qt client libraries and every Wi-Fi/cellular module build and load,
  but their indicators show an empty state until an OS network service
  speaks those DBus APIs. EmberBSD network management is a separate OS
  track.
