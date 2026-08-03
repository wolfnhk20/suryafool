// src/utils/platform.js
// Platform detection utilities

export function getPlatform() {
  const platform = process.platform;
  const arch = process.arch;
  
  if (platform === 'win32') return 'windows';
  if (platform === 'darwin') return 'macos';
  if (platform === 'linux') return 'linux';
  return 'unknown';
}

export function getArch() {
  return process.arch;
}

export function isWindows() {
  return process.platform === 'win32';
}

export function isMacOS() {
  return process.platform === 'darwin';
}

export function isLinux() {
  return process.platform === 'linux';
}