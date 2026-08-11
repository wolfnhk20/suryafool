import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'fs';
import os from 'os';
import path from 'path';
import { findRepoRoot, getRepoRoot, _resetCacheForTests } from './repo-root.js';

function makeTempTree() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'suryafool-test-'));
  const repo = path.join(root, 'fake-repo');
  const subdir = path.join(repo, 'suryafool-cli', 'src', 'utils');
  const manifestDir = path.join(repo, 'bootstrap');
  fs.mkdirSync(subdir, { recursive: true });
  fs.mkdirSync(manifestDir, { recursive: true });
  fs.writeFileSync(path.join(manifestDir, 'manifest.yaml'), 'dependencies: []\n');
  return { root, repo, subdir };
}

describe('findRepoRoot', () => {
  test('walks up and finds manifest two levels deep', () => {
    const { repo, subdir } = makeTempTree();
    assert.equal(findRepoRoot(subdir), repo);
  });

  test('returns the start dir itself if manifest is there', () => {
    const { repo } = makeTempTree();
    assert.equal(findRepoRoot(repo), repo);
  });

  test('returns null when no ancestor contains the manifest', () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'suryafool-no-'));
    assert.equal(findRepoRoot(dir), null);
  });

  test('handles an already-absolute start path', () => {
    const { repo, subdir } = makeTempTree();
    assert.equal(findRepoRoot(path.resolve(subdir)), repo);
  });
});

describe('getRepoRoot', () => {
  test('memoizes the result across calls', () => {
    _resetCacheForTests();
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'suryafool-memo-'));
    fs.mkdirSync(path.join(dir, 'bootstrap'), { recursive: true });
    fs.writeFileSync(path.join(dir, 'bootstrap', 'manifest.yaml'), 'dependencies: []\n');
    const a = getRepoRoot({ startDir: dir });
    const b = getRepoRoot();
    assert.equal(a, b);
    assert.equal(a, dir);
    _resetCacheForTests();
  });
});
