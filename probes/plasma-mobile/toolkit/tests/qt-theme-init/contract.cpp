// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// Origin: EmberBSD (AI-assisted). Actual Qt bodies with controlled services.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>

#define CHECK(e) do { if (!(e)) { std::fprintf(stderr, "FAIL contract: %s\n", #e); std::exit(1); } } while (false)
#define Q_ASSERT(e) CHECK(e)

static int generation = 1;
static int requested, notifications, iconCache, iconTheme, fileCache;
static int styleUpdates, paletteValue, fontValue, hintValue, fontClears;
static int contrastValue, motionValue, colorValue, refreshed;
static bool repeatConstructor;
static int kdeSessionVersion = 6;
static bool fullSession = true;
struct QStringList {};
struct QString {};
struct QByteArray {
    int value;
    int toInt() const { return value; }
};
static QByteArray qgetenv(const char *name) { CHECK(std::strcmp(name, "KDE_SESSION_VERSION") == 0); return {kdeSessionVersion}; }
struct QStandardPaths {
    enum Location { GenericConfigLocation };
    static QStringList standardLocations(Location) { return {}; }
};
struct QPlatformTheme {
    virtual ~QPlatformTheme() = default;
    int colorScheme() const { return generation * 10 + 1; }
    int contrastPreference() const { return generation * 10 + 2; }
    int motionPreference() const { return generation * 10 + 3; }
};
struct QStyleHints {};
struct QAccessibilityHints {};
struct QAccessibilityHintsPrivate {
    static QAccessibilityHintsPrivate *get(QAccessibilityHints *) { static QAccessibilityHintsPrivate p; return &p; }
    void updateContrastPreference(int v) { contrastValue = v; }
    void updateMotionPreference(int v) { motionValue = v; }
};
struct QStyleHintsPrivate {
    static QStyleHintsPrivate *get(QStyleHints *) { static QStyleHintsPrivate p; return &p; }
    void update(const QPlatformTheme *);
    void updateColorScheme(int v) { colorValue = v; ++styleUpdates; }
    QAccessibilityHints *accessibilityHints() const { static QAccessibilityHints a; return &a; }
};
struct QEvent {
    enum Type { ThemeChange };
    explicit QEvent(Type) {}
};
struct QGuiApplication;
static QGuiApplication *qGuiApp;
struct QGuiApplication {
    static QStyleHints *styleHints() { CHECK(qGuiApp); static QStyleHints s; return &s; }
    static void sendSpontaneousEvent(QGuiApplication *app, QEvent *) { CHECK(app); ++notifications; }
};
struct QWindowSystemInterfacePrivate { struct ThemeChangeEvent {}; };
struct Integration;
struct QGuiApplicationPrivate {
    static QPlatformTheme *platform_theme;
    static Integration *platform_integration;
    static QPlatformTheme *platformTheme() { return platform_theme; }
    static QGuiApplicationPrivate *instance() { static QGuiApplicationPrivate p; return qGuiApp ? &p : nullptr; }
    static void processThemeChanged(QWindowSystemInterfacePrivate::ThemeChangeEvent *);
    void handleThemeChanged();
    static void updatePalette() { CHECK(platform_theme); paletteValue = generation; }
};
QPlatformTheme *QGuiApplicationPrivate::platform_theme;
Integration *QGuiApplicationPrivate::platform_integration;
struct QIconPrivate { static void clearIconCache() { ++iconCache; } };
struct QIconLoader {
    static QIconLoader *instance() { static QIconLoader p; return &p; }
    void updateSystemTheme() { ++iconTheme; }
};
struct QAbstractFileIconProviderPrivate { static void clearIconTypeCache() { ++fileCache; } };
static int applicationResourceFlags;
static constexpr int ApplicationFontExplicitlySet = 1;
static int applicationFontMutex;
struct ScopedLock { ~ScopedLock() {} };
static ScopedLock qt_scoped_lock(int &) { return {}; }
static void clearFontUnlocked() { ++fontClears; fontValue = 0; }
static void initFontUnlocked() { CHECK(QGuiApplicationPrivate::platform_theme); fontValue = generation; }
static void initThemeHints() { CHECK(QGuiApplicationPrivate::platform_theme); hintValue = generation; }
struct QFont { static void initialize() { initFontUnlocked(); } };
struct QWindowSystemInterface {
    // Controlled service: KWin QPA enables synchronous event delivery.
    static void handleThemeChange() { ++requested; QGuiApplicationPrivate::processThemeChanged(nullptr); }
};
struct QKdeThemePrivate {
    QKdeThemePrivate(const QStringList &, int) {}
    void refresh();
};
struct QGenericUnixTheme : QPlatformTheme {
    explicit QGenericUnixTheme(QKdeThemePrivate *d) : data(d) {}
    QKdeThemePrivate *d_func() { return data.get(); }
    std::unique_ptr<QKdeThemePrivate> data;
};
struct QKdeTheme : QGenericUnixTheme {
    QKdeTheme(const QStringList &, int);
    static QPlatformTheme *createKdeTheme();
};
struct Integration {
    QPlatformTheme *createPlatformTheme(const QString &) { return fullSession ? QKdeTheme::createKdeTheme() : new QPlatformTheme; }
};
#include "actual-theme.h"

static void checkState(int expected, int expectedFont)
{
    CHECK(colorValue == expected * 10 + 1);
    CHECK(contrastValue == expected * 10 + 2);
    CHECK(motionValue == expected * 10 + 3);
    CHECK(paletteValue == expected && fontValue == expectedFont && hintValue == expected);
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    QGuiApplication app;
    Integration integration;
    qGuiApp = &app;
    QGuiApplicationPrivate::platform_integration = &integration;
    repeatConstructor = std::strcmp(argv[1], "constructor-repeat") == 0;
    if (std::strcmp(argv[1], "version-refused") == 0) {
        kdeSessionVersion = 3;
        install_theme();
        CHECK(refreshed == 0 && requested == 0 && QGuiApplicationPrivate::platform_theme == nullptr);
        kdeSessionVersion = 6;
    }
    const bool generic = std::strcmp(argv[1], "generic") == 0;
    fullSession = !generic;
    install_theme();
    CHECK(QGuiApplicationPrivate::platform_theme != nullptr);
    CHECK(refreshed == (generic ? 0 : 1) && requested == (generic ? 0 : repeatConstructor ? 2 : 1));
    CHECK(styleUpdates == 0 && notifications == 0 && iconCache == 0 && iconTheme == 0 && fileCache == 0);
    initialize_state();
    CHECK(styleUpdates == 1);
    checkState(1, 1);
    if (std::strcmp(argv[1], "no-app") == 0) {
        qGuiApp = nullptr;
        QWindowSystemInterface::handleThemeChange();
        CHECK(styleUpdates == 1 && notifications == 0 && iconCache == 0 && iconTheme == 0 && fileCache == 0);
    } else if (std::strcmp(argv[1], "late") == 0 || std::strcmp(argv[1], "explicit-font") == 0) {
        const bool explicitFont = std::strcmp(argv[1], "explicit-font") == 0;
        if (explicitFont) {
            applicationResourceFlags = ApplicationFontExplicitlySet;
            fontValue = 99;
        }
        generation = 2;
        static_cast<QKdeTheme *>(QGuiApplicationPrivate::platform_theme)->d_func()->refresh();
        CHECK(styleUpdates == 2);
        checkState(2, explicitFont ? 99 : 2);
        CHECK(notifications == 1 && iconCache == 1 && iconTheme == 1 && fileCache == 1);
        CHECK(fontClears == (explicitFont ? 0 : 1));
    }
    delete QGuiApplicationPrivate::platform_theme;
    QGuiApplicationPrivate::platform_theme = nullptr;
    QGuiApplicationPrivate::platform_integration = nullptr;
    qGuiApp = nullptr;
    std::puts("PASS actual-source theme lifecycle");
    return 0;
}
