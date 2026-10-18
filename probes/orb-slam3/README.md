# ORB-SLAM3 headless source profile

This source profile builds the current stable ORB-SLAM3 v1.0 release
for offline C++ SLAM consumers with the common OpenCV 5.0.0 and Eigen 5.0.1
libraries. ORB-SLAM3 owns visual SLAM and map optimization; EmberBSD Ports
owns this adaptation, installation and API contracts.

The installed API contracts and a complete recorded RGB-D trajectory have
passed on EmberBSD AArch64 in a VM. This is a source probe, not a pkgsrc package
or evidence of live camera, IMU or physical-board support.

## Dependencies and build

Use the verified common OpenCV/Eigen installation from
[robotics-foundations](../robotics-foundations/README.md). Additional native
requirements are a C++17 compiler, CMake 3.20+, Ninja, Boost 1.91 serialization,
OpenSSL 3.5+, tar, patch and `sha256` or `shasum`. curl is needed without a
source cache. Python, ROS, Pangolin and a graphical session are not required
by this headless configuration.

```sh
JOBS=1 sh probes/orb-slam3/build.sh /absolute/new-work /absolute/common-prefix /absolute/cache
sh probes/orb-slam3/test.sh /absolute/new-work /absolute/common-prefix
```

`COMMON_PREFIX` supplies Eigen. OpenCV defaults to that same installation;
set `OPENCV_PREFIX=/absolute/opencv-prefix` for all three scripts when the
selected common OpenCV provider is installed separately. This selects one
OpenCV 5.0.0 installation for building and testing; it does not create another
version. Installed consumers can set `OpenCV_DIR` to its `lib/cmake/opencv5`.

The cache contains all filenames from [sources.tsv](sources.tsv). The work
directory must be new; its parent must exist. All paths must be absolute and
contain no whitespace. Original sources are verified before selective
extraction. The approximately 600 MB upstream archive is retained once in
the cache. Selected code/configuration and the compressed vocabulary occupy
about 45 MB before vocabulary expansion; duplicated upstream datasets are
omitted. Logs remain under `work/logs`, preserving errors and exit status.

On a small builder use `JOBS=1` and provide enough memory for the upstream
translation units. The recipe uses ordinary `-O2`, preserves those units and
leaves inherited resource limits unchanged. `BUILD_DATA_KIB` or `BUILD_VM_KIB`
can optionally select a caller-chosen limit; neither has a default value.

The result installs only under `work/install`. The ORB-modified g2o/DBoW2
libraries live in `lib/orb-slam3` and their headers under `include/ORB_SLAM3`.
No system library or package is replaced. The vocabulary, calibration example,
source manifest and full license notices are installed in `share/orb-slam3`.

```cmake
find_package(ORB_SLAM3 1.0.0 EXACT CONFIG REQUIRED)
target_link_libraries(my_application PRIVATE ORB_SLAM3::ORB_SLAM3)
```

Set CMake's prefix path to both installations and include `<System.h>`.
Construct `ORB_SLAM3::System` with `bUseViewer=false`; `true` throws
`std::invalid_argument` before loading inputs. The public exported target
propagates the required headless definition. Rendering code and its calls are
excluded rather than replaced by stubs. A viewer-enabled build is outside
the validated profile and would require actual Pangolin and OpenCV highgui.

Call `Shutdown()` after the last `Track*` call and before saving trajectories.
The adaptation joins LocalMapping, LoopClosing and global bundle adjustment
workers. Concurrent tracking/shutdown from different application threads is
outside this profile's contract.

## Installed API checks

The separate installed consumer binds headers and libraries to the selected
prefixes. Tests cover:

- ORB descriptors from deterministic image texture and a Sophus/Eigen transform.
- Explicit rejection of a requested viewer in a headless build.
- Three successive GBA workers, mutex-aware joining and ownership release.
- Real g2o iteration-loop cancellation through the atomic stop API, and
  continued operation of its original `bool*` setter.
- A completing GBA cannot erase the new loop correction mapping stop request.
- A viewer callback avoids joining itself; an external caller can join it.
- An unavailable frame pose retains its current timestamp and is marked lost,
  so trajectory export cannot invent repeated successful poses.
- Real idle-system startup/shutdown; NetBSD's native thread count must return
  to its baseline, including immediate repeated shutdown.

The GBA ownership fixture uses a delayed worker to test joining; it does not
claim numerical bundle-adjustment validation. Numerical SLAM and trajectory
comparison belong to a separate dataset consumer. The script checks dynamic
linkage and rejects viewer libraries in the headless build.

For a cause-specific regression against the exact original upstream Shutdown,
run `sh probes/orb-slam3/regression-shutdown.sh ABS_WORK ABS_COMMON_PREFIX ABS_CACHE`.
It extracts the pinned original method with its license into a temporary test
library, expects the thread-count contract to fail with that method preloaded,
then expects the installed adaptation to pass. A second mutation restores the
inherited wrong GBA/LocalMapping stop ordering; an atomic handshake makes its
lost-stop failure deterministic. A third mutation restores the inherited
missing-pose timestamp/lost-flag operations and must fail the actual history
helper contract. All runs have CTest timeouts;
the installed production library is never replaced.

## Native and offline dataset validation

On 2026-10-07 the profile built with whole upstream translation units and
ordinary O2 on the EMBER64 `b4f718d` VM, NetBSD 11.0 userland, GCC 12.5,
CMake 4.3.3 and Ninja 1.13.2. The builder had 4 GiB RAM and temporary 4 GiB
swap; this observation is not a minimum memory specification. All eight
installed contracts passed. The three cause-specific mutation regressions
each failed for the expected reason and passed with the installed adaptation.
The idle-system thread count returned from three to its baseline of one.
Dynamic linkage selected the chosen common OpenCV provider and no viewer.

The selected first dataset is TUM RGB-D `freiburg1_desk`: 23.4 seconds with
9.263 metres of ground-truth motion, images, depth and loop closures.
The [official download page](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download)
describes the sequence; the original archive is 344,011,403 bytes.
[TUM's license](https://cvg.cit.tum.de/data/datasets/rgbd-dataset#license)
is CC BY 4.0 for data. Attribute J. Sturm, N. Engelhard, F. Endres,
W. Burgard and D. Cremers, *A Benchmark for the Evaluation of RGB-D SLAM
Systems*, IROS 2012. Dataset download is separate and is not stored in Git.

The [standalone RGB-D example](https://github.com/oxtech-ember/EmberBSD-Examples/tree/main/robotics/orb-slam3-rgbd)
uses libpng 1.6.58 to decode original RGB and uint16 depth images. Two runs
with OpenCV/DUtils seed zero tracked and exported all 573 associated frames,
with fixed-scale SE(3) ATE RMSE 0.01762/0.01712 m and maximum error
0.07675/0.06781 m. Both returned to one native thread after shutdown.
Its README records timing, RSS, input failures and strict export coverage.

A run without the explicit DUtils seed is retained as a negative control:
487/573 frames and the inherited missing-pose history defect; repairing its
export does not accept its tracking. Two controlled
passes do not prove that the seed caused or eliminated the earlier tracking
failure, general scheduling stability, real-time throughput or a long run.

[Provenance](PROVENANCE.md) records original licenses, internal dependency
origins and the local adaptation.
