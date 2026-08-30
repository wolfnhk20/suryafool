// src/components/EvidenceFeed.test.js
// Phase 2.7.8 — unit tests for the EvidenceFeed compact line formatter.
// The pure `formatEvidenceLine` maps a raw evidence record to the display
// fields rendered by the panel, and must never crash on missing metadata.

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { formatEvidenceLine } from './evidenceFormat.js';

describe('formatEvidenceLine (Phase 2.7.8)', () => {
  test('maps a Wi-Fi evidence record to compact fields', () => {
    const line = formatEvidenceLine({
      kind: 'wifi_pmkid',
      target_entity_id: '02:00:00:00:00:01',
      target_entity_type: 'wifi_network',
      source_capability: 'wifi.capture',
      source_action: 'pmkid',
      summary: 'Captured PMKID (WPA3) from LAB-INTERNAL (02:00:00:00:00:01).',
    });
    assert.equal(line.kind, 'wifi_pmkid');
    assert.equal(line.target, '02:00:00:00:00:01');
    assert.equal(line.source, 'wifi.capture.pmkid');
    assert.equal(line.summary, 'Captured PMKID (WPA3) from LAB-INTERNAL (02:00:00:00:00:01).');
    assert.equal(line.domain, 'wifi');
  });

  test('maps a BLE evidence record and distinguishes the domain', () => {
    const line = formatEvidenceLine({
      kind: 'ble_pairing',
      target_entity_id: 'AA:BB:CC:00:00:01',
      source_capability: 'ble.gatt',
      source_action: 'pair',
      summary: 'Paired with Suryafool-BLE-Target (AA:BB:CC:00:00:01).',
    });
    assert.equal(line.kind, 'ble_pairing');
    assert.equal(line.source, 'ble.gatt.pair');
    assert.equal(line.domain, 'ble');
  });

  test('does not crash when optional fields are missing', () => {
    assert.deepEqual(formatEvidenceLine({}), {
      kind: 'unknown', target: '—', source: '—', summary: '(no summary)', domain: 'other',
    });
  });

  test('does not crash on null / undefined / non-object input', () => {
    const fallback = { kind: 'unknown', target: '—', source: '—', summary: '(no summary)', domain: 'other' };
    assert.deepEqual(formatEvidenceLine(null), fallback);
    assert.deepEqual(formatEvidenceLine(undefined), fallback);
    assert.deepEqual(formatEvidenceLine('junk'), fallback);
  });

  test('coerces non-string fields instead of crashing', () => {
    const line = formatEvidenceLine({ kind: 123, source_action: '' });
    assert.equal(line.kind, '123');
    assert.equal(line.source, '—');
    assert.equal(line.domain, 'other');
  });

  // Phase 2.8.1 — Sub-GHz evidence kinds flow through the same domain
  // mapping (no wifi/ble prefix => 'other'), so the TUI EvidenceFeed
  // keeps rendering subghz_capture / subghz_analysis evidence without a
  // TUI source change. This locks the assumption so a future TUI refactor
  // that silently drops the 'other' bucket is caught.
  describe('formatEvidenceLine (Phase 2.8.1 Sub-GHz)', () => {
    test('maps a subghz_capture evidence record to domain other', () => {
      const line = formatEvidenceLine({
        kind: 'subghz_capture',
        target_entity_id: '433.920MHz-OOK',
        target_entity_type: 'subghz_signal',
        source_capability: 'subghz.capture',
        source_action: 'signal',
        summary: 'Captured 1024 samples of OOK signal at 433.92 MHz (clean).',
      });
      assert.equal(line.kind, 'subghz_capture');
      assert.equal(line.target, '433.920MHz-OOK');
      assert.equal(line.source, 'subghz.capture.signal');
      assert.equal(line.domain, 'other');
    });

    test('maps a subghz_analysis evidence record to domain other', () => {
      const line = formatEvidenceLine({
        kind: 'subghz_analysis',
        target_entity_id: '868.300MHz-FSK',
        source_capability: 'subghz.discovery',
        source_action: 'analyze',
        summary: 'Analyzed captured signal at 868.30 MHz: likely LoRa / sub-GHz IoT.',
      });
      assert.equal(line.kind, 'subghz_analysis');
      assert.equal(line.source, 'subghz.discovery.analyze');
      assert.equal(line.domain, 'other');
    });

    test('subghz evidence stays visually distinct from wifi/ble', () => {
      const c = formatEvidenceLine({ kind: 'subghz_capture' });
      const w = formatEvidenceLine({ kind: 'wifi_pmkid' });
      const b = formatEvidenceLine({ kind: 'ble_pairing' });
      assert.equal(c.domain, 'other');
      assert.equal(w.domain, 'wifi');
      assert.equal(b.domain, 'ble');
      // Three distinct domains — Sub-GHz evidence is not misfiled into
      // wifi or ble in the EvidenceFeed.
      assert.ok(c.domain !== w.domain && c.domain !== b.domain);
    });
  });

  // Phase 2.8.2 — NFC evidence kinds flow through the same domain
  // mapping (no wifi/ble prefix => 'other'), just like Sub-GHz.
  describe('formatEvidenceLine (Phase 2.8.2 NFC)', () => {
    test('maps a nfc_read evidence record to domain other', () => {
      const line = formatEvidenceLine({
        kind: 'nfc_read',
        target_entity_id: '04:DE:AD:BE:EF:01',
        target_entity_type: 'nfc_tag',
        source_capability: 'nfc.discovery',
        source_action: 'read',
        summary: 'Read 2 NDEF record(s) from NTAG215 tag 04:DE:AD:BE:EF:01.',
      });
      assert.equal(line.kind, 'nfc_read');
      assert.equal(line.target, '04:DE:AD:BE:EF:01');
      assert.equal(line.source, 'nfc.discovery.read');
      assert.equal(line.domain, 'other');
    });

    test('NFC evidence is visually distinct from wifi/ble', () => {
      const n = formatEvidenceLine({ kind: 'nfc_read' });
      const w = formatEvidenceLine({ kind: 'wifi_pmkid' });
      const b = formatEvidenceLine({ kind: 'ble_pairing' });
      assert.equal(n.domain, 'other');
      assert.equal(w.domain, 'wifi');
      assert.equal(b.domain, 'ble');
      assert.ok(n.domain !== w.domain && n.domain !== b.domain);
    });
  });

  // Phase 2.8.3 — Infrared evidence kinds flow through the same domain
  // mapping (no wifi/ble prefix => 'other'), just like Sub-GHz and NFC.
  describe('formatEvidenceLine (Phase 2.8.3 Infrared)', () => {
    test('maps an ir_analysis evidence record to domain other', () => {
      const line = formatEvidenceLine({
        kind: 'ir_analysis',
        target_entity_id: 'ir-lab-remote',
        target_entity_type: 'ir_signal',
        source_capability: 'infrared',
        source_action: 'analyze',
        summary: 'Analyzed IR burst ir-lab-remote (38.0 kHz / 900 ms): likely NEC consumer-IR frame.',
      });
      assert.equal(line.kind, 'ir_analysis');
      assert.equal(line.target, 'ir-lab-remote');
      assert.equal(line.source, 'infrared.analyze');
      assert.equal(line.domain, 'other');
    });

    test('maps an ir_transmit evidence record to domain other', () => {
      const line = formatEvidenceLine({
        kind: 'ir_transmit',
        target_entity_id: 'ir-lab-remote',
        target_entity_type: 'ir_signal',
        source_capability: 'infrared',
        source_action: 'transmit',
        summary: 'Replayed analyzed IR burst ir-lab-remote (38.0 kHz / 900 ms).',
      });
      assert.equal(line.kind, 'ir_transmit');
      assert.equal(line.target, 'ir-lab-remote');
      assert.equal(line.source, 'infrared.transmit');
      assert.equal(line.domain, 'other');
    });

    test('IR evidence is visually distinct from wifi/ble', () => {
      const a = formatEvidenceLine({ kind: 'ir_analysis' });
      const t = formatEvidenceLine({ kind: 'ir_transmit' });
      const w = formatEvidenceLine({ kind: 'wifi_pmkid' });
      const b = formatEvidenceLine({ kind: 'ble_pairing' });
      assert.equal(a.domain, 'other');
      assert.equal(t.domain, 'other');
      assert.equal(w.domain, 'wifi');
      assert.equal(b.domain, 'ble');
      assert.ok(a.domain !== w.domain && a.domain !== b.domain);
    });
  });

  // Phase 2.8.4 — Zigbee mesh evidence kinds flow through the same domain
  describe('formatEvidenceLine (Phase 2.8.4 Zigbee)', () => {
    test('maps a zigbee_join evidence record to domain other', () => {
      const line = formatEvidenceLine({
        kind: 'zigbee_join',
        target_entity_id: '00:15:8D:00:00:00:00:04',
        target_entity_type: 'zigbee_node',
        source_capability: 'zigbee.discovery',
        source_action: 'join',
        summary: 'Device 00:15:8D:00:00:00:00:04 joined PAN 0x1A2B as 0x0003.',
      });
      assert.equal(line.kind, 'zigbee_join');
      assert.equal(line.target, '00:15:8D:00:00:00:00:04');
      assert.equal(line.source, 'zigbee.discovery.join');
      assert.equal(line.domain, 'other');
    });

    test('zigbee evidence is visually distinct from wifi/ble', () => {
      const z = formatEvidenceLine({ kind: 'zigbee_join' });
      const w = formatEvidenceLine({ kind: 'wifi_pmkid' });
      const b = formatEvidenceLine({ kind: 'ble_pairing' });
      assert.equal(z.domain, 'other');
      assert.equal(w.domain, 'wifi');
      assert.equal(b.domain, 'ble');
      assert.ok(z.domain !== w.domain && z.domain !== b.domain);
    });
  });
});
