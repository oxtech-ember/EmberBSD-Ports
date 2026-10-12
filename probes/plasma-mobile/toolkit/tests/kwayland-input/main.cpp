// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted), installed KWayland wire-button regression.
#include <KWayland/Client/fakeinput.h>
#include <QCoreApplication>
#include <wayland-client.h>
#include <wayland-server.h>
#include "fake-input-client.h"
#include "fake-input-server.h"
#include <sys/socket.h>
#include <array>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>

struct Event { uint32_t button, state; };
struct Server {
    wl_display *display;
    std::array<Event, 32> events{};
    std::atomic<unsigned> count{0};
    std::atomic<bool> done{false};
};
static void require(bool condition, const char *message)
{
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", message);
        std::exit(1);
    }
}
static void button(wl_client *, wl_resource *resource, uint32_t code, uint32_t state)
{
    auto *server = static_cast<Server *>(wl_resource_get_user_data(resource));
    const unsigned index = server->count.load();
    require(index < server->events.size(), "unexpected event overflow");
    server->events[index] = {code, state};
    server->count.store(index + 1);
}
static void destroy(wl_client *, wl_resource *resource) { wl_resource_destroy(resource); }
static void bind(wl_client *client, void *data, uint32_t version, uint32_t id)
{
    static const struct org_kde_kwin_fake_input_interface implementation = {
        nullptr, nullptr, button, nullptr, nullptr, nullptr, nullptr,
        nullptr, nullptr, nullptr, nullptr, destroy, nullptr
    };
    auto *resource = wl_resource_create(client, &org_kde_kwin_fake_input_interface, version, id);
    require(resource != nullptr, "create fake-input resource");
    wl_resource_set_implementation(resource, &implementation, data, nullptr);
}
static void announced(void *data, wl_registry *registry, uint32_t name, const char *interface, uint32_t version)
{
    if (std::strcmp(interface, org_kde_kwin_fake_input_interface.name) == 0) {
        require(version >= 6, "fake-input version");
        *static_cast<org_kde_kwin_fake_input **>(data) = static_cast<org_kde_kwin_fake_input *>(
            wl_registry_bind(registry, name, &org_kde_kwin_fake_input_interface, 6));
    }
}
static void removed(void *, wl_registry *, uint32_t) {}
int main(int argc, char **argv)
{
    QCoreApplication application(argc, argv);
    for (unsigned cycle = 0; cycle != 4; ++cycle) {
        int sockets[2];
        require(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0, "socketpair");
        Server server{wl_display_create()};
        require(server.display != nullptr, "create display");
        auto *global = wl_global_create(server.display, &org_kde_kwin_fake_input_interface, 6, &server, bind);
        require(global != nullptr, "create private global");
        require(wl_client_create(server.display, sockets[1]) != nullptr, "create private client");
        auto *display = wl_display_connect_to_fd(sockets[0]);
        require(display != nullptr, "connect private socket");
        std::thread dispatch([&server] {
            while (!server.done.load()) {
                require(wl_event_loop_dispatch(wl_display_get_event_loop(server.display), 10) >= 0, "dispatch server");
                wl_display_flush_clients(server.display);
            }
        });
        org_kde_kwin_fake_input *manager = nullptr;
        auto *registry = wl_display_get_registry(display);
        static const wl_registry_listener listener = {announced, removed};
        wl_registry_add_listener(registry, &listener, &manager);
        require(wl_display_roundtrip(display) >= 0 && manager != nullptr, "discover private fake-input global");
        {
            KWayland::Client::FakeInput input;
            input.setup(manager);
            const Qt::MouseButton buttons[] = {Qt::LeftButton, Qt::RightButton, Qt::MiddleButton};
            for (const auto key : buttons) {
                input.requestPointerButtonPress(key);
                input.requestPointerButtonRelease(key);
                input.requestPointerButtonClick(key);
            }
            input.requestPointerButtonClick(quint32(0x113));
            input.requestPointerButtonClick(Qt::NoButton);
            input.requestPointerButtonPress(Qt::BackButton);
            require(wl_display_roundtrip(display) >= 0, "flush button requests");
            require(server.count.load() == 14, "unsupported button emitted a request or supported button was lost");
            for (unsigned i = 0; i != 14; ++i) {
                const uint32_t expected = i < 12 ? 0x110 + i / 4 : 0x113;
                if (server.events[i].button != expected || server.events[i].state != (i % 2 == 0 ? 1U : 0U)) {
                    std::fprintf(stderr, "event %u: code=%#x state=%u expected=%#x\n", i,
                        server.events[i].button, server.events[i].state, expected);
                    require(false, "Wayland button code/state mismatch");
                }
            }
        }
        require(wl_display_roundtrip(display) >= 0, "destroy input resource");
        wl_registry_destroy(registry);
        wl_display_disconnect(display);
        server.done.store(true);
        dispatch.join();
        wl_display_destroy_clients(server.display);
        wl_global_destroy(global);
        wl_display_destroy(server.display);
    }
    std::puts("PASS: four installed KWayland cycles; 56 exact button wire events, unsupported buttons rejected");
}
