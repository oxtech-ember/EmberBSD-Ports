# Source provenance

The selected tests belong to OpenCV and its original contributors.
Use the common [OpenCV source pin](../../../../pkgsrc/local-robotics/opencv5/files/SOURCE).

| Item | Value |
| --- | --- |
| Release | OpenCV 5.0.0, 2026-06-06 |
| Commit | `40738fb16ceddb5fb3fea747585f7ce6abb0605b` |
| Archive | <https://github.com/opencv/opencv/archive/refs/tags/5.0.0.tar.gz> |
| SHA256 | `b0528f5a1d379d59d4701cb28c36e22214cc51cf64594e5b56f2d3e6c0233095` |

Compiled files are `modules/core/test/{test_main,test_mat,test_operations}.cpp`
and `modules/ts/src/{ts,ts_arrtest,ts_func,ts_gtest,ts_perf,ts_tags}.cpp`.
Keep these files unchanged. The adapter does not copy them into Ports.
The final native and target test sources were compared with the verified archive.
All nine translation units were identical. The provider's portability patches
affect its CPU, filesystem and dynamic-loader implementation, not these tests.

OpenCV distributes its main license as Apache-2.0. The selected sources also
retain the older OpenCV BSD notice and GoogleTest's BSD notice. Preserve those
original source notices and reproduce them with redistributed test binaries.
The adapter, runner and selection were prepared by EmberBSD with AI assistance.
They are local validation support and have not been accepted upstream.
