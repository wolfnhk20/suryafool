// src/backend/backend.js
// Backend manager for coordinating binary execution

import BinaryManager from './binary.js';

export class BackendManager {
  constructor() {
    this.binary = new BinaryManager();
  }

  async run(command, args = [], options = {}) {
    return this.binary.run([command, ...args], options);
  }

  async checkHealth() {
    try {
      await this.binary.run(['doctor'], { timeout: 5000 });
      return { healthy: true };
    } catch (err) {
      return { healthy: false, error: err.message };
    }
  }
}

export default BackendManager;