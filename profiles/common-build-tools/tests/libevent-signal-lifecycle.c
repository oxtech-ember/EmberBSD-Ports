/* SPDX-License-Identifier: BSD-2-Clause */
/* Copyright (c) 2026 EmberBSD contributors. */
#include <event2/event.h>
#include <signal.h>
#include <stdlib.h>
struct state { struct event *event; int count; };
static void callback(evutil_socket_t fd, short events, void *arg) {
    struct state *s = arg; (void)fd; (void)events; ++s->count;
    event_free(s->event); s->event = NULL;
}
int main(void) {
    struct event_base *base = event_base_new();
    struct state state = {0};
    if (!base) return 1;
    state.event = evsignal_new(base, SIGUSR1, callback, &state);
    if (!state.event) return 2;
    event_active(state.event, EV_SIGNAL, 1);
    if (event_base_loop(base, EVLOOP_NONBLOCK) < 0 || state.count != 1) return 3;
    event_base_free(base);
    return 0;
}
