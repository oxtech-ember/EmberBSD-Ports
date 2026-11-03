# Bosch BMI270 SensorAPI source

Upstream: `boschsensortec/BMI270_SensorAPI`, version 2.113.0 at commit
`41129fcfe39c583ee5462d79195741945d51c1fe`, downloaded from the exact commit
archive. Copyright Bosch Sensortec GmbH, BSD-3-Clause; retain the upstream
`LICENSE` with the installed source.

The Ports patch set adds NetBSD kernel type-header support and removes two
unnecessary const-dropping casts passed to `bmi2_set_regs()`. The latter keeps
the published `const uint8_t *` API contract and allows kernel builds with
`-Wcast-qual`; it does not change the API behavior.

The package supplies the public base BMI2/BMI270 interfaces and Bosch base
configuration data only. Espressif's component includes separate Circle and
Toy custom firmware in prebuilt libraries under a custom license; those are
not copied or used here. The selected package can be consumed as a prepared
source directory by base consumers while retaining the native kernel ABI.
