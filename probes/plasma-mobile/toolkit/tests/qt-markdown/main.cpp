// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// Origin: EmberBSD (AI-assisted). Upstream status: not submitted.
#include <QTextCursor>
#include <QTextDocument>

int main()
{
    QTextDocument doc;
    doc.setMarkdown(QStringLiteral("---\ntitle: sample\n---\n\n~~strike~~ [^note]\n\n[^note]: footnote\n"),
                    QTextDocument::MarkdownDialectGitHub);
    if (doc.metaInformation(QTextDocument::FrontMatter) != QStringLiteral("title: sample\n"))
        return 1;
    if (doc.toPlainText() != QStringLiteral("strike ^note"))
        return 2;
    QTextCursor cursor(&doc);
    cursor.setPosition(1);
    cursor.movePosition(QTextCursor::NextCharacter, QTextCursor::KeepAnchor);
    return cursor.charFormat().fontStrikeOut() ? 0 : 3;
}
