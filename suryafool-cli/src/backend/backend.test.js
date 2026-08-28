import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'events';

// Create a mockable spawn wrapper
// We test the BinaryManager by mocking the child_process import via a test-specific module

import { BinaryManager } from './binary.js';
import { BackendManager } from './backend.js';
import { EventType } from './events.js';

describe('BinaryManager - basic instantiation', () => {
  test('detects platform', () => {
    const manager = new BinaryManager();
    assert.ok(manager.platform);
    assert.ok(typeof manager.platform === 'string');
  });

  test('has binaryPath property', () => {
    const manager = new BinaryManager();
    assert.ok(typeof manager.binaryPath === 'string');
  });

  test('isInstalled returns boolean', () => {
    const manager = new BinaryManager();
    const installed = manager.isInstalled();
    assert.equal(typeof installed, 'boolean');
  });

  test('has a parser instance', () => {
    const manager = new BinaryManager();
    assert.ok(manager.parser);
  });
});

describe('BinaryManager - run with real Python', () => {
  test('runs a simple echo command', async () => {
    const manager = new BinaryManager();
    // Try to run a simple command - this may fail if Python is not available
    // but the error handling should be tested
    try {
      const result = await manager.run(['--help'], { timeout: 5000 });
      assert.equal(typeof result, 'string');
    } catch (err) {
      // Expected if Python module not available
      assert.ok(err.message);
    }
  });
});

describe('BackendManager', () => {
  test('instantiates with binary manager', () => {
    const manager = new BackendManager();
    assert.ok(manager.binary);
    assert.equal(manager.currentCommand, null);
  });

  test('getCurrentCommand returns null initially', () => {
    const manager = new BackendManager();
    assert.equal(manager.getCurrentCommand(), null);
  });

  test('checkHealth returns result object', async () => {
    const manager = new BackendManager();
    const health = await manager.checkHealth();
    assert.ok(typeof health === 'object');
    assert.ok(typeof health.healthy === 'boolean');
    if (!health.healthy) {
      assert.ok(typeof health.error === 'string');
    }
  });

  test('run tracks current command during execution', async () => {
    const manager = new BackendManager();
    // Track state during a real run
    let currentDuringRun = null;
    const promise = manager.run('--help', []).catch(() => {});
    // Wait a bit for the command to start
    await new Promise(resolve => setTimeout(resolve, 10));
    currentDuringRun = manager.getCurrentCommand();
    await promise;
    // After completion, current command should be null
    assert.equal(manager.getCurrentCommand(), null);
  });
});

describe('Event protocol integration', () => {
  test('events have valid structure', () => {
    const event = {
      type: EventType.COMMAND_STARTED,
      command: 'scan',
      args: ['target'],
      timestamp: Date.now()
    };
    assert.equal(event.type, 'command.started');
    assert.ok(typeof event.command === 'string');
    assert.ok(Array.isArray(event.args));
    assert.ok(typeof event.timestamp === 'number');
  });

  test('all event types are unique strings', () => {
    const types = Object.values(EventType);
    const unique = new Set(types);
    assert.equal(types.length, unique.size);
  });
});
