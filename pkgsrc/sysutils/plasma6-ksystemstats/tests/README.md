# NetBSD ifaddrs counter lifetime regression

`network-ifaddrs-lifetime.cpp` includes the production
`files/network/NetBsdBackend.cpp` and calls `IfaddrsNetDevice::update()` with
controlled `getifaddrs()` and `freeifaddrs()` adapters. The adapter frees the
complete address list before the sensor values are checked, so AddressSanitizer
detects reads through a saved `ifa_data` pointer.

Run it with the selected native Clang++:

```sh
CXX=/path/to/native-clang++ tests/run-network-ifaddrs-lifetime.sh
```

The test also checks getifaddrs failure, a successful list without link
counters, address updates, and counter reset rate behavior. It validates the
source-level ownership and counter contract on the host; it does not replace
the ordinary target package build or runtime checks.
