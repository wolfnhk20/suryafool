// src/utils/repo-root.js
// Walk up the directory tree to locate the Suryafool repo root (marked by
// bootstrap/manifest.yaml). Used to anchor Python subprocess cwd and child
// module resolution so the CLI works regardless of where it's invoked from.

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function findRepoRoot(startDir) {
  let dir = path.resolve(startDir);
  while (true) {
    if (fs.existsSync(path.join(dir, 'bootstrap', 'manifest.yaml'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

let cached = null;
let warned = false;

export function getRepoRoot(opts = {}) {
  if (cached) return cached;
  const fromEnv = process.env.SURYAFOOL_REPO_ROOT;
  const start = opts.startDir || fromEnv || __dirname;
  const found = findRepoRoot(start);
  if (found) {
    cached = found;
  } else {
    if (!warned) {
      console.warn('[suryafool] bootstrap/manifest.yaml not found; falling back to cwd');
      warned = true;
    }
    cached = process.cwd();
  }
  return cached;
}

export function _resetCacheForTests() {
  cached = null;
  warned = false;
}
