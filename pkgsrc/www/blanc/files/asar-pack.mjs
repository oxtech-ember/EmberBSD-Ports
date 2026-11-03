#!/usr/bin/env node
// SPDX-License-Identifier: BSD-2-Clause
// Copyright (c) 2026 EmberBSD contributors.
// Origin: EmberBSD (AI-assisted). This invokes the pinned upstream ASAR tool.

import path from 'node:path';
import { pathToFileURL } from 'node:url';

const [asarModule, appRoot, outputPath] = process.argv.slice(2);
if (!asarModule || !appRoot || !outputPath) {
  throw new Error('Usage: asar-pack.mjs asar-module app-root output-asar');
}

const { createPackage, listPackage } = await import(pathToFileURL(asarModule).href);
await createPackage(appRoot, outputPath);
const files = listPackage(outputPath, { isPack: true }).map((entry) =>
  entry.replace(/^pack\s*:\s*/, '').replace(/^\/+/, ''),
);
process.stdout.write(JSON.stringify({ files }) + '\n');
