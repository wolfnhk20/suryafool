// src/backend/binary.js
// Python binary manager for CLI wrapper

import { execFileSync, spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';
import { OutputParser } from './parser.js';
import { EventType, commandOutput, commandProgress, findingCreated, agentStatus, vulnFound, logEvent, errorEvent, commandStarted, commandCompleted, commandFailed } from './events.js';
import { getRepoRoot } from '../utils/repo-root.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class BinaryManager {
  constructor() {
    this.platform = this.detectPlatform();
    this.binaryPath = this.getBinaryPath();
    this.parser = new OutputParser();
  }

  detectPlatform() {
    const platform = os.platform();
    const arch = os.arch();
    const map = {
      'win32-x64': 'windows-x64',
      'linux-x64': 'linux-x64',
      'linux-arm64': 'linux-arm64',
      'darwin-x64': 'macos-x64',
      'darwin-arm64': 'macos-arm64',
    };
    return map[`${platform}-${arch}`] || `${platform}-${arch}`;
  }

  getBinaryPath() {
    const binaryName = this.platform.startsWith('windows') ? 'suryafool.exe' : 'suryafool';
    return path.join(__dirname, '..', 'bin', this.platform, binaryName);
  }

  isInstalled() {
    return fs.existsSync(this.binaryPath);
  }

  async fetchBinary(version = 'latest') {
    // Try to use the Python module directly if binary not available
    try {
      execFileSync('python', ['-m', 'bootstrap.agent', '--help'], { stdio: 'ignore' });
      return 'python -m bootstrap.agent';
    } catch {
      // Binary download not implemented - Python module is the primary path
      throw new Error('Binary download not configured. Please ensure the Python bootstrap.agent module is available.');
    }
  }

  run(args = [], options = {}) {
    const { onEvent, timeout = 0, module: moduleName = 'bootstrap.agent', ...spawnOptions } = options;

    return new Promise((resolve, reject) => {
      // Try Python module first (primary path)
      const useBinary = this.isInstalled();
      const cmd = useBinary ? this.binaryPath : 'python';
      const argsToUse = useBinary ? args : ['-m', moduleName, ...args];
      
      let proc;
      try {
        proc = spawn(cmd, argsToUse, {
          cwd: getRepoRoot(),
          stdio: ['pipe', 'pipe', 'pipe'],
          env: { ...process.env, ...spawnOptions.env },
        });
      } catch (spawnError) {
        reject(new Error(`Failed to spawn process: ${spawnError.message}`));
        return;
      }

      let stdout = '';
      let stderr = '';
      let timeoutId = null;
      let resolved = false;

      // Set up timeout if specified
      if (timeout > 0) {
        timeoutId = setTimeout(() => {
          if (!resolved) {
            resolved = true;
            proc.kill('SIGTERM');
            // Give it a moment to terminate gracefully
            setTimeout(() => {
              if (!proc.killed) proc.kill('SIGKILL');
            }, 1000);
            reject(new Error(`Command timed out after ${timeout}ms`));
          }
        }, timeout);
      }

      const cleanup = () => {
        if (timeoutId) clearTimeout(timeoutId);
        // Remove listeners to prevent memory leaks
        proc.stdout.removeAllListeners();
        proc.stderr.removeAllListeners();
        proc.removeAllListeners();
      };

      // Emit command started event
      if (onEvent) {
        onEvent(commandStarted(argsToUse[0] || 'unknown', argsToUse.slice(1)));
      }

      proc.stdout.on('data', (data) => {
        const chunk = data.toString();
        stdout += chunk;
        
        // Parse structured events from output
        const events = this.parser.parse(chunk);
        for (const event of events) {
          if (onEvent) onEvent(event);
        }
      });

      proc.stderr.on('data', (data) => {
        const chunk = data.toString();
        stderr += chunk;
        // Also parse stderr for structured events
        const events = this.parser.parse(chunk);
        for (const event of events) {
          if (onEvent) onEvent(event);
        }
      });

      proc.on('close', (code) => {
        if (resolved) return;
        resolved = true;
        cleanup();
        
        // Flush any remaining buffered output
        const flushEvents = this.parser.flush();
        for (const event of flushEvents) {
          if (onEvent) onEvent(event);
        }

        if (code === 0) {
          if (onEvent) onEvent(commandCompleted(argsToUse[0] || 'unknown', stdout));
          resolve(stdout);
        } else {
          const error = stderr || `Exit code ${code}`;
          if (onEvent) onEvent(commandFailed(argsToUse[0] || 'unknown', error));
          reject(new Error(error));
        }
      });

      proc.on('error', (err) => {
        if (resolved) return;
        resolved = true;
        cleanup();
        if (onEvent) onEvent(commandFailed(argsToUse[0] || 'unknown', err.message));
        reject(new Error(`Process error: ${err.message}`));
      });
    });
  }
}

export default BinaryManager;