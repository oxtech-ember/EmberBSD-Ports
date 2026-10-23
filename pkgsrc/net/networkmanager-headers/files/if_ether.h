/* NetBSD shim for the Linux header: the NM public headers need only
   the Ethernet address length and protocol constants. */
#ifndef NM_SHIM_LINUX_IF_ETHER_H
#define NM_SHIM_LINUX_IF_ETHER_H
#include <sys/types.h>
#ifndef ETH_ALEN
#define ETH_ALEN 6
#endif
#ifndef ETH_P_IP
#define ETH_P_IP 0x0800
#endif
#ifndef ETH_P_IPV6
#define ETH_P_IPV6 0x86dd
#endif
#ifndef ETH_P_ARP
#define ETH_P_ARP 0x0806
#endif
#endif
