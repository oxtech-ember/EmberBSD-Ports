# Chromium CRDTP traits regression

Run `run.py` with the selected SDK host prefix, SDK source and lock root, a prepared Chromium source view, its Darwin host GN `toolchain.ninja`, and a separate writable work directory. It generates host build flags from that GN toolchain, builds the actual CRDTP and Chromium string sources, and checks UTF-16 and malformed input behavior. The current runner uses Darwin linker `-dead_strip`; target execution and other host linkers are not covered.
