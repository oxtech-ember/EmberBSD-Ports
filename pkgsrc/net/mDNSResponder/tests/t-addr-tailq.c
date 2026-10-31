/* SPDX-License-Identifier: BSD-2-Clause */
#include <stddef.h>
#include "mdns_addr_tailq.h"

struct reference_entry {
	STAILQ_ENTRY(reference_entry) links;
};
STAILQ_HEAD(reference_head, reference_entry);

_Static_assert(sizeof(((struct mdns_addr_with_port *)0)->__entries) ==
    sizeof(((struct reference_entry *)0)->links), "queue entry layout");
_Static_assert(sizeof(struct mdns_addr_tailq) == sizeof(struct reference_head),
    "queue head layout");
_Static_assert(offsetof(struct mdns_addr_tailq, stqh_first) ==
    offsetof(struct reference_head, stqh_first), "first offset");
_Static_assert(offsetof(struct mdns_addr_tailq, stqh_last) ==
    offsetof(struct reference_head, stqh_last), "last offset");

int
main(void)
{
	struct mdns_addr_tailq queue;
	struct mdns_addr_with_port a = {0}, b = {0}, c = {0};

	STAILQ_INIT(&queue);
	if (!STAILQ_EMPTY(&queue)) return 1;
	STAILQ_INSERT_HEAD(&queue, &a, __entries);
	STAILQ_INSERT_TAIL(&queue, &b, __entries);
	STAILQ_INSERT_TAIL(&queue, &c, __entries);
	if (STAILQ_FIRST(&queue) != &a || STAILQ_NEXT(&a, __entries) != &b ||
	    STAILQ_NEXT(&b, __entries) != &c) return 2;
	STAILQ_REMOVE(&queue, &b, mdns_addr_with_port, __entries);
	if (STAILQ_NEXT(&a, __entries) != &c) return 3;
	STAILQ_REMOVE_HEAD(&queue, __entries);
	STAILQ_REMOVE_HEAD(&queue, __entries);
	if (!STAILQ_EMPTY(&queue)) return 4;
	STAILQ_INSERT_TAIL(&queue, &b, __entries);
	return STAILQ_FIRST(&queue) != &b;
}
