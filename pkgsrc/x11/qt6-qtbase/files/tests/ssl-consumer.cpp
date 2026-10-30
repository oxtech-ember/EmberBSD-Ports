// SPDX-License-Identifier: BSD-2-Clause
// A loopback-only TLS handshake with a fixture-specific trust anchor.
#include <QtCore/QCoreApplication>
#include <QtCore/QFile>
#include <QtCore/QTimer>
#include <QtNetwork/QHostAddress>
#include <QtNetwork/QSslCertificate>
#include <QtNetwork/QSslConfiguration>
#include <QtNetwork/QSslKey>
#include <QtNetwork/QSslSocket>
#include <QtNetwork/QTcpServer>
#include <cstdio>
#include <memory>

class TlsListener final : public QTcpServer
{
public:
    QSslCertificate cert;
    QSslKey key;
protected:
    void incomingConnection(qintptr fd) override
    {
        auto *server = new QSslSocket(this);
        if (!server->setSocketDescriptor(fd)) { delete server; return; }
        server->setLocalCertificate(cert);
        server->setPrivateKey(key);
        auto received = std::make_shared<QByteArray>();
        QObject::connect(server, &QSslSocket::readyRead, server, [server, received] {
            received->append(server->readAll());
            if (*received == "ember-tls-ping")
                server->write("ember-tls-pong");
        });
        server->startServerEncryption();
    }
};

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    if (argc != 3 || !QSslSocket::supportsSsl())
        return 1;
    const QByteArray version = QSslSocket::sslLibraryVersionString().toUtf8();
    if (!version.startsWith("OpenSSL 3."))
        return 2;
    QFile certFile(QString::fromLocal8Bit(argv[1]));
    QFile keyFile(QString::fromLocal8Bit(argv[2]));
    if (!certFile.open(QIODevice::ReadOnly) || !keyFile.open(QIODevice::ReadOnly))
        return 3;
    const QSslCertificate cert(&certFile, QSsl::Pem);
    const QSslKey key(&keyFile, QSsl::Rsa, QSsl::Pem);
    if (cert.isNull() || key.isNull())
        return 4;
    TlsListener listener;
    listener.cert = cert;
    listener.key = key;
    if (!listener.listen(QHostAddress::LocalHost, 0))
        return 5;
    QSslSocket client;
    QSslConfiguration config = client.sslConfiguration();
    config.setCaCertificates({cert});
    config.setPeerVerifyMode(QSslSocket::VerifyPeer);
    client.setSslConfiguration(config);
    int result = 6;
    QByteArray received;
    QObject::connect(&client, &QSslSocket::encrypted, &app, [&] { client.write("ember-tls-ping"); });
    QObject::connect(&client, &QSslSocket::readyRead, &app, [&] {
        received.append(client.readAll());
        if (received == "ember-tls-pong") { result = 0; app.quit(); }
    });
    QTimer::singleShot(10000, &app, &QCoreApplication::quit);
    client.connectToHostEncrypted(QStringLiteral("127.0.0.1"), listener.serverPort(),
                                  QStringLiteral("localhost"));
    app.exec();
    std::printf("Qt SSL backend: %s; loopback handshake: %s\n", version.constData(), result ? "FAIL" : "PASS");
    return result;
}
