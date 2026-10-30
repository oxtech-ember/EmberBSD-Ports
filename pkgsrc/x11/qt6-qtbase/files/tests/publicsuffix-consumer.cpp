// SPDX-License-Identifier: BSD-2-Clause
// Exercise the Qt suffix policy and its cookie-jar consumer together.
#include <QtCore/QCoreApplication>
#include <QtCore/QString>
#include <QtCore/QUrl>
#include <QtNetwork/QNetworkCookie>
#include <QtNetwork/QNetworkCookieJar>
#include <cstdio>

extern bool qIsEffectiveTLD(QStringView);

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    const struct { const char *domain; bool suffix; bool cookie; } cases[] = {
        {"com", true, false}, {"sendai.jp", false, true},
        {"foo.sendai.jp", true, false}, {"sch.uk", false, true},
        {"foo.sch.uk", true, false}, {"ck", true, false},
        {"www.ck", false, true}, {"example.invalid", false, true},
        {"рф", true, false}, {"xn--p1ai", true, false},
        {".com", false, false}, {"co.uk.", false, true},
    };
    for (const auto &item : cases) {
        const QString domain = QString::fromUtf8(item.domain);
        const bool suffix = qIsEffectiveTLD(QStringView(domain));
        QNetworkCookieJar jar;
        QNetworkCookie cookie("probe", "1");
        cookie.setDomain(domain);
        const bool accepted = jar.setCookiesFromUrl({cookie},
            QUrl(QStringLiteral("https://host.") + domain + QStringLiteral("/")));
        if (suffix != item.suffix || accepted != item.cookie) {
            std::fprintf(stderr, "%s: suffix=%d cookie=%d\n", item.domain,
                         int(suffix), int(accepted));
            return 1;
        }
    }
    return 0;
}
