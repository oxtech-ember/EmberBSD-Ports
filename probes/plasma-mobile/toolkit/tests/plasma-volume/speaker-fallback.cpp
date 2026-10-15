// SPDX-License-Identifier: BSD-2-Clause
// Origin: EmberBSD (AI-assisted).
// Execute the production bodies with real Qt and libcanberra declarations.
// The external backend double controls synchronous failures and completion.
#include <QObject>
#include <QStringList>
#include <canberra.h>
#include <cstdio>
#include <cstdlib>
#include <new>

static void *callbackData;
static unsigned int callbackDeletes;
void *operator new(std::size_t size)
{
    if (void *p = std::malloc(size)) {
        return p;
    }
    throw std::bad_alloc();
}
void operator delete(void *p) noexcept
{
    if (p && p == callbackData) {
        ++callbackDeletes;
    }
    std::free(p);
}
void operator delete(void *p, std::size_t) noexcept
{
    ::operator delete(p);
}

struct ca_context {};
struct ca_proplist {};
static ca_context context;
static ca_proplist properties;
static bool contextAvailable = true;
static unsigned int requests;
static unsigned int failuresBeforeSuccess;
static ca_finish_callback_t pending;
static QStringList events;
static QString currentEvent;
static unsigned int propertyCreates;
static unsigned int propertyDestroys;
static bool deviceRestored;

extern "C" {
int ca_context_set_driver(ca_context *, const char *) { return CA_SUCCESS; }
int ca_context_change_device(ca_context *, const char *device)
{
    deviceRestored = device == nullptr;
    return CA_SUCCESS;
}
int ca_proplist_create(ca_proplist **p)
{
    ++propertyCreates;
    *p = &properties;
    return CA_SUCCESS;
}
int ca_proplist_destroy(ca_proplist *) { ++propertyDestroys; return CA_SUCCESS; }
int ca_proplist_sets(ca_proplist *, const char *key, const char *value)
{
    if (qstrcmp(key, CA_PROP_EVENT_ID) == 0) {
        currentEvent = QString::fromLatin1(value);
    }
    return CA_SUCCESS;
}
int ca_context_play_full(ca_context *, uint32_t, ca_proplist *, ca_finish_callback_t callback, void *data)
{
    callbackData = data;
    events.append(currentEvent);
    if (requests++ < failuresBeforeSuccess) {
        return CA_ERROR_NOTFOUND;
    }
    pending = callback;
    return CA_SUCCESS;
}
const char *ca_strerror(int) { return "fixture playback error"; }
}

namespace PulseAudioQt {
class Sink {
public:
    unsigned int index() const { return 7; }
};
class CanberraContext {
public:
    static CanberraContext *instance() { static CanberraContext singleton; return &singleton; }
    ca_context *canberra() { return contextAvailable ? &context : nullptr; }
};
}
class SoundThemeConfig : public QObject {
public:
    explicit SoundThemeConfig(QObject *parent) : QObject(parent) {}
    QString soundTheme() const { return QStringLiteral("fixture"); }
};
class SpeakerTest : public QObject {
public:
    explicit SpeakerTest(QObject *parent = nullptr);
    PulseAudioQt::Sink *sink() const;
    void setSink(PulseAudioQt::Sink *sink);
    QStringList playingChannels() const;
    void playingFinished(const QString &name, int errorCode);
    void testChannel(const QString &name);
    void sinkChanged() {}
    void playingChannelsChanged() { ++changes; }
    void showErrorMessage(const QString &) { ++errors; }
    unsigned int changes = 0;
    unsigned int errors = 0;
private:
    PulseAudioQt::Sink *m_sink = nullptr;
    QStringList m_playingChannels;
    SoundThemeConfig *m_config = nullptr;
};
#include "speaker-source.inc"

static unsigned int checks;
static unsigned int failures;
static void check(bool condition, const char *message)
{
    ++checks;
    if (!condition) {
        ++failures;
        std::fprintf(stderr, "FAIL: %s\n", message);
    }
}
int main()
{
    PulseAudioQt::Sink sink;
    for (unsigned int failedRequests = 0; failedRequests <= 3; ++failedRequests) {
        for (const QString &channel : {QStringLiteral("front-left"), QStringLiteral("lfe")}) {
            callbackData = nullptr;
            callbackDeletes = requests = propertyCreates = propertyDestroys = 0;
            failuresBeforeSuccess = failedRequests;
            pending = nullptr;
            events.clear();
            deviceRestored = false;
            SpeakerTest speaker;
            speaker.setSink(&sink);
            speaker.testChannel(channel);
            check(requests == (failedRequests < 3 ? failedRequests + 1 : 3), "fallback request count");
            check(events.value(0) == (channel == QStringLiteral("lfe") ? QStringLiteral("audio-channel-rear-center") : QStringLiteral("audio-channel-front-left")), "first sound");
            if (requests > 1) check(events.value(1) == QStringLiteral("audio-test-signal"), "second sound");
            if (requests > 2) check(events.value(2) == QStringLiteral("bell-window-system"), "third sound");
            check(propertyCreates == 1 && propertyDestroys == 1, "property ownership");
            check(deviceRestored, "device selection restored");
            if (failedRequests == 3) {
                check(!pending && callbackDeletes == 1, "all failed requests must release callback data");
                check(speaker.playingChannels().isEmpty() && speaker.errors == 1 && speaker.changes == 2, "synchronous failure notification");
                // Keep the negative control leak-free after detecting its cause.
                if (!callbackDeletes) delete static_cast<CallbackData *>(callbackData);
            } else {
                check(pending && callbackDeletes == 0, "successful request transfers callback ownership");
                check(speaker.playingChannels() == QStringList{channel} && speaker.errors == 0, "successful request remains pending");
                pending(&context, 0, CA_SUCCESS, callbackData);
                check(callbackDeletes == 1 && speaker.playingChannels().isEmpty() && speaker.changes == 2, "completion releases callback data exactly once");
            }
            callbackData = nullptr;
        }
    }
    contextAvailable = false;
    requests = 0;
    SpeakerTest speaker;
    speaker.testChannel(QStringLiteral("front-left"));
    check(requests == 0 && speaker.playingChannels().isEmpty() && speaker.changes == 0, "missing context returns without backend requests");
    std::printf("%u checks, %u failures\n", checks, failures);
    return failures ? 1 : 0;
}
