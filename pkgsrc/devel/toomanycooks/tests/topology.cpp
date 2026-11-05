#define TMC_IMPL
#define TMC_USE_HWLOC
#include <tmc/all_headers.hpp>
#include <hwloc.h>
#include <cstdio>
int main(int argc, char **argv) {
 hwloc_topology_t h;
 if (hwloc_topology_init(&h)) return 2;
 if (argc > 1 && hwloc_topology_set_synthetic(h, argv[1])) return 3;
 if (hwloc_topology_load(h)) return 4;
 std::printf("core=%d pu=%d\n", hwloc_get_nbobjs_by_type(h,HWLOC_OBJ_CORE), hwloc_get_nbobjs_by_type(h,HWLOC_OBJ_PU)); std::fflush(stdout);
 tmc::topology::detail::Topology result;
 tmc::topology::detail::query_internal_parse(h, result);
 size_t cpus = 0;
 for (const auto &core : result.cores) { if (!core.cpuset || core.pus.empty()) return 5; if (argc > 1 && core.cache != nullptr) return 7; if (argc > 1 && core.pus.size() != (argv[1][0] == 'p' ? 1u : 2u)) return 8; cpus += core.pus.size(); }
 std::printf("tmc_cores=%zu tmc_pus=%zu\n", result.cores.size(), cpus);
 if (cpus == 0 || (argc > 1 && (cpus != 4 || result.cores.size() != (argv[1][0] == 'p' ? 4u : 2u)))) return 6;
 std::puts("parse=PASS");
 hwloc_topology_destroy(h);
 return 0;
}
