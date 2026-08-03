// src/utils/config.js
// Configuration file management

import fs from 'fs';
import path from 'path';
import os from 'os';

const CONFIG_DIR = path.join(os.homedir(), '.suryafool');
const CONFIG_FILE = path.join(CONFIG_DIR, 'config.json');

const DEFAULT_CONFIG = {
  lab_mode: false,
  log_level: 'INFO',
  theme: 'cyberpunk',
  api_keys: {
    openrouter: '',
    opencode_zen: ''
  }
};

export function getConfigPath() {
  return CONFIG_FILE;
}

export function loadConfig() {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      const data = fs.readFileSync(CONFIG_FILE, 'utf8');
      return { ...DEFAULT_CONFIG, ...JSON.parse(data) };
    }
  } catch (err) {
    console.error('Failed to load config:', err.message);
  }
  return DEFAULT_CONFIG;
}

export function saveConfig(config) {
  try {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
    return true;
  } catch (err) {
    console.error('Failed to save config:', err.message);
    return false;
  }
}

export function getConfig(key) {
  const config = loadConfig();
  return key.split('.').reduce((obj, k) => obj?.[k], config);
}

export function setConfig(key, value) {
  const config = loadConfig();
  const parts = key.split('.');
  let obj = config;
  for (let i = 0; i < parts.length - 1; i++) {
    if (!obj[parts[i]]) obj[parts[i]] = {};
    obj = obj[parts[i]];
  }
  obj[parts[parts.length - 1]] = value;
  return saveConfig(config);
}

export { DEFAULT_CONFIG };