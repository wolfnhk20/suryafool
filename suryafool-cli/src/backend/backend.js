// src/backend/backend.js
// Backend manager for coordinating binary execution with structured events

import BinaryManager from './binary.js';
import { EventType, commandStarted, commandOutput, commandProgress, commandCompleted, commandFailed, findingCreated, agentStatus, vulnFound, logEvent, errorEvent } from './events.js';

export class BackendManager {
  constructor() {
    this.binary = new BinaryManager();
    this.currentCommand = null;
  }

  /**
   * Run a command with structured event callbacks
   * @param {string} command - Command to execute
   * @param {string[]} args - Command arguments
   * @param {Object} options - Options
   * @param {Function} options.onEvent - Callback for structured events
   * @param {number} options.timeout - Timeout in ms
   * @param {string} options.module - Python module to invoke (default: 'bootstrap.agent')
   * @returns {Promise<string>} - Command output on success
   */
  async run(command, args = [], options = {}) {
    this.currentCommand = { command, args, startTime: Date.now() };

    return this.binary.run([command, ...args], {
      onEvent: options.onEvent,
      timeout: options.timeout,
      env: options.env,
      module: options.module,
    }).then((output) => {
      this.currentCommand = null;
      return output;
    }).catch((error) => {
      this.currentCommand = null;
      throw error;
    });
  }

  /**
   * Check backend health by running doctor command
   */
  async checkHealth() {
    try {
      await this.binary.run(['doctor'], { timeout: 5000 });
      return { healthy: true };
    } catch (err) {
      return { healthy: false, error: err.message };
    }
  }

  /**
   * Get current command info
   */
  getCurrentCommand() {
    return this.currentCommand;
  }
}

export default BackendManager;