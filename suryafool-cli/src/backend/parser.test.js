import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'events';
import { Readable } from 'stream';

// We need to mock child_process for unit tests
// Since ESM modules can't be easily mocked, we'll create a test that
// tests the parser and event handling logic directly

import { OutputParser } from './parser.js';
import { EventType, isValidEvent, commandStarted, commandCompleted, commandFailed } from './events.js';

describe('OutputParser edge cases', () => {
  test('handles single line JSON without newline', () => {
    const parser = new OutputParser();
    const event = { type: EventType.COMMAND_STARTED, command: 'scan' };
    const events = parser.parse(JSON.stringify(event));
    // No newline means it stays in buffer
    assert.equal(events.length, 0);
    // Flush should return it
    const flushed = parser.flush();
    assert.equal(flushed.length, 1);
  });

  test('handles very large JSON output', () => {
    const parser = new OutputParser();
    const largeData = 'x'.repeat(10000);
    const event = { type: EventType.COMMAND_OUTPUT, line: largeData };
    const events = parser.parse(JSON.stringify(event) + '\n');
    assert.equal(events.length, 1);
    assert.equal(events[0].line.length, 10000);
  });

  test('handles special characters in output', () => {
    const parser = new OutputParser();
    const specialChars = 'Special chars: \n\t\\"\\\'\u0000\u00ff';
    const event = { type: EventType.COMMAND_OUTPUT, line: specialChars };
    const events = parser.parse(JSON.stringify(event) + '\n');
    assert.equal(events.length, 1);
    assert.equal(events[0].line, specialChars);
  });

  test('handles multiple lines in single chunk', () => {
    const parser = new OutputParser();
    const event1 = { type: EventType.COMMAND_STARTED, command: 'scan' };
    const event2 = { type: EventType.SCAN_PROGRESS, progress: 50 };
    const event3 = { type: EventType.COMMAND_COMPLETED, command: 'scan' };
    const input = [
      JSON.stringify(event1),
      JSON.stringify(event2),
      JSON.stringify(event3)
    ].join('\n') + '\n';
    
    const events = parser.parse(input);
    assert.equal(events.length, 3);
    assert.equal(events[0].type, EventType.COMMAND_STARTED);
    assert.equal(events[1].type, EventType.SCAN_PROGRESS);
    assert.equal(events[2].type, EventType.COMMAND_COMPLETED);
  });

  test('handles partial JSON across multiple chunks', () => {
    const parser = new OutputParser();
    const event = { type: EventType.COMMAND_STARTED, command: 'scan', args: ['target1', 'target2'] };
    const json = JSON.stringify(event);
    
    // Split the JSON across multiple chunks
    const chunk1 = json.substring(0, 20);
    const chunk2 = json.substring(20, 40);
    const chunk3 = json.substring(40) + '\n';
    
    assert.equal(parser.parse(chunk1).length, 0);
    assert.equal(parser.parse(chunk2).length, 0);
    const events = parser.parse(chunk3);
    assert.equal(events.length, 1);
    assert.equal(events[0].type, EventType.COMMAND_STARTED);
  });
});

describe('Event type validation', () => {
  test('all event types are non-empty strings', () => {
    for (const [key, value] of Object.entries(EventType)) {
      assert.equal(typeof value, 'string', `${key} should be string`);
      assert.ok(value.length > 0, `${key} should not be empty`);
    }
  });

  test('event types follow dot notation pattern', () => {
    for (const value of Object.values(EventType)) {
      // Allow simple names like 'log' and 'error' as well as dotted names
      assert.match(value, /^[a-z]+(_[a-z]+)*(\.[a-z_]+)?$/, `${value} should follow pattern`);
    }
  });
});

describe('EVIDENCE_CREATED parsing (Phase 2.7.8)', () => {
  test('evidence.created is a valid registered event type', () => {
    assert.ok(EventType.EVIDENCE_CREATED, 'evidence.created constant exists');
    const ev = { type: EventType.EVIDENCE_CREATED, evidence: { kind: 'wifi_pmkid' } };
    assert.ok(isValidEvent(ev));
  });

  test('parses a Wi-Fi evidence event from the stream', () => {
    const parser = new OutputParser();
    const event = {
      type: EventType.EVIDENCE_CREATED,
      evidence: {
        kind: 'wifi_eapol_handshake',
        target_entity_id: '02:00:00:00:00:01',
        target_entity_type: 'wifi_network',
        source_capability: 'wifi.capture',
        source_action: 'handshake',
        summary: 'Captured 4 EAPOL frames (WPA3) from LAB-INTERNAL (02:00:00:00:00:01).',
      },
      source_action_id: 'req-1',
      run_id: 'run-1',
    };
    const events = parser.parse(JSON.stringify(event) + '\n');
    assert.equal(events.length, 1);
    assert.equal(events[0].type, EventType.EVIDENCE_CREATED);
    assert.equal(events[0].evidence.kind, 'wifi_eapol_handshake');
    assert.equal(events[0].evidence.source_capability, 'wifi.capture');
    assert.equal(events[0].source_action_id, 'req-1');
  });

  test('parses a BLE evidence event from the stream', () => {
    const parser = new OutputParser();
    const event = {
      type: EventType.EVIDENCE_CREATED,
      evidence: {
        kind: 'ble_secure_write',
        target_entity_id: 'AA:BB:CC:00:00:01',
        target_entity_type: 'ble_device',
        source_capability: 'ble.gatt',
        source_action: 'write',
        summary: 'Wrote secure value to characteristic battery.',
      },
    };
    const events = parser.parse(JSON.stringify(event) + '\n');
    assert.equal(events[0].type, EventType.EVIDENCE_CREATED);
    assert.equal(events[0].evidence.kind, 'ble_secure_write');
  });

  test('multiple evidence events parse independently in one chunk', () => {
    const parser = new OutputParser();
    const ws = { type: EventType.EVIDENCE_CREATED, evidence: { kind: 'wifi_pmkid' } };
    const bs = { type: EventType.EVIDENCE_CREATED, evidence: { kind: 'ble_pairing' } };
    const events = parser.parse([JSON.stringify(ws), JSON.stringify(bs)].join('\n') + '\n');
    assert.equal(events.length, 2);
    assert.deepEqual(events.map((e) => e.evidence.kind), ['wifi_pmkid', 'ble_pairing']);
  });
});
