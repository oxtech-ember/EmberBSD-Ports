// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.
//
// EmberBSD/NetBSD: discover DRM-backed GPUs via /dev/dri + PCI config ioctls.
// Linux uses /sys/class/drm; NetBSD has no sysfs, so we scan PCI class 0x03
// when at least one openable DRM node exists.

#include "core/platform/device_discovery.h"

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>

#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include <sys/ioctl.h>
#include <dev/pci/pciio.h>
#include <dev/pci/pcireg.h>

#include "core/common/common.h"
#include "core/common/logging/logging.h"

namespace onnxruntime {
namespace {

bool DriNodeExists() {
  DIR* dir = opendir("/dev/dri");
  if (!dir) {
    return false;
  }
  bool found = false;
  while (dirent* entry = readdir(dir)) {
    const char* name = entry->d_name;
    if (std::strncmp(name, "renderD", 7) == 0 || std::strncmp(name, "card", 4) == 0) {
      found = true;
      break;
    }
  }
  closedir(dir);
  return found;
}

// Prefer an openable render node; NetBSD advertises dead minors (ENODEV) for
// card1–3 / renderD129+. Opening card0 (display master) for compute metadata
// is unnecessary — Vulkan/Dawn should stay on renderD*.
bool HasOpenableDriNode(std::string& first_ok_out) {
  DIR* dir = opendir("/dev/dri");
  if (!dir) {
    return false;
  }
  const int dir_fd = dirfd(dir);
  // Complete the render-node pass before considering a display-master node.
  // Some advertised minors have no device attached and return ENODEV.
  for (const char* prefix : {"renderD", "card"}) {
    rewinddir(dir);
    while (dirent* entry = readdir(dir)) {
      const char* name = entry->d_name;
      if (std::strncmp(name, prefix, std::strlen(prefix)) != 0) {
        continue;
      }
      const int fd = openat(dir_fd, name, O_RDWR | O_CLOEXEC);
      if (fd < 0) {
        continue;
      }
      close(fd);
      first_ok_out = name;
      closedir(dir);
      return true;
    }
  }
  closedir(dir);
  return false;
}

int OpenPciDevice() {
  static const char* kPaths[] = {"/dev/pci0", "/dev/pci", nullptr};
  for (int i = 0; kPaths[i]; ++i) {
    const int fd = open(kPaths[i], O_RDONLY | O_CLOEXEC);
    if (fd >= 0) {
      return fd;
    }
  }
  return -1;
}

bool ReadPciId(int pci_fd, unsigned bus, unsigned device, unsigned function,
               uint16_t& vendor_id, uint16_t& device_id, unsigned& pci_class,
               unsigned& pci_subclass) {
  struct pciio_bdf_cfgreg req {};
  req.bus = bus;
  req.device = device;
  req.function = function;
  req.cfgreg.reg = PCI_ID_REG;
  if (ioctl(pci_fd, PCI_IOC_BDF_CFGREAD, &req) < 0) {
    return false;
  }
  const uint32_t id = req.cfgreg.val;
  vendor_id = static_cast<uint16_t>(PCI_VENDOR(id));
  device_id = static_cast<uint16_t>(PCI_PRODUCT(id));
  if (vendor_id == 0 || vendor_id == 0xffff) {
    return false;
  }

  req.cfgreg.reg = PCI_CLASS_REG;
  if (ioctl(pci_fd, PCI_IOC_BDF_CFGREAD, &req) < 0) {
    return false;
  }
  const uint32_t cr = req.cfgreg.val;
  pci_class = PCI_CLASS(cr);
  pci_subclass = PCI_SUBCLASS(cr);
  return true;
}

std::vector<OrtHardwareDevice> DiscoverGpusViaPci() {
  std::vector<OrtHardwareDevice> gpus;
  std::string dri_node;
  if (!HasOpenableDriNode(dri_node)) {
    if (DriNodeExists()) {
      LOGS_DEFAULT(WARNING) << "NetBSD DRM nodes exist under /dev/dri but none open (ENODEV?); "
                               "skipping GPU discovery";
    }
    return gpus;
  }

  const int pci_fd = OpenPciDevice();
  if (pci_fd < 0) {
    LOGS_DEFAULT(WARNING) << "NetBSD GPU discovery: cannot open /dev/pci0: " << std::strerror(errno);
    return gpus;
  }

  // Conventional PCI BDF fields: 8-bit bus, 5-bit device, 3-bit function.
  for (unsigned bus = 0; bus < 256; ++bus) {
    for (unsigned device = 0; device < 32; ++device) {
      for (unsigned function = 0; function < 8; ++function) {
        uint16_t vendor_id = 0;
        uint16_t device_id = 0;
        unsigned pci_class = 0;
        unsigned pci_subclass = 0;
        if (!ReadPciId(pci_fd, bus, device, function, vendor_id, device_id, pci_class, pci_subclass)) {
          continue;
        }
        if (pci_class != PCI_CLASS_DISPLAY) {
          continue;
        }

        OrtHardwareDevice gpu{};
        gpu.vendor_id = vendor_id;
        gpu.device_id = device_id;
        gpu.type = OrtHardwareDeviceType_GPU;
        gpu.metadata.Add("pci_bus_id", MakeString(bus, ":", device, ".", function));
        gpu.metadata.Add("dri_node", dri_node);
        // VGA / 3D controllers are typically the GPUs we care about for WebGPU.
        if (pci_subclass == 0x00 || pci_subclass == 0x02) {
          gpus.push_back(std::move(gpu));
        }
      }
    }
  }

  close(pci_fd);
  return gpus;
}

}  // namespace

std::unordered_set<OrtHardwareDevice> DeviceDiscovery::DiscoverDevicesForPlatform() {
  std::unordered_set<OrtHardwareDevice> devices;
  devices.emplace(GetCpuDeviceFromCPUIDInfo());

  auto gpus = DiscoverGpusViaPci();
  devices.insert(std::make_move_iterator(gpus.begin()), std::make_move_iterator(gpus.end()));
  return devices;
}

}  // namespace onnxruntime
