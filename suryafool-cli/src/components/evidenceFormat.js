// src/components/evidenceFormat.js
// Phase 2.7.8 — pure helpers for the EvidenceFeed panel. Kept separate from
// the JSX component so the compact-line mapping is unit-testable with
// node:test (no React/Ink required).

/**
 * Map a raw evidence record to compact display fields. Strictly defensive —
 * any missing/unexpected field falls back gracefully so a malformed event
 * never crashes the panel:
 *   { kind, target, source, summary, domain }
 * `domain` is 'wifi' | 'ble' | 'other', derived from the kind prefix so the
 * two evidence families are visually distinguishable.
 */
export function formatEvidenceLine(record = {}) {
  const ev = record && typeof record === 'object' ? record : {};
  const kind = String(ev.kind || 'unknown');
  const domain = kind.startsWith('wifi') ? 'wifi' : (kind.startsWith('ble') ? 'ble' : 'other');
  return {
    kind,
    target: String(ev.target_entity_id || '—'),
    source: [ev.source_capability, ev.source_action].filter(Boolean).join('.') || '—',
    summary: String(ev.summary || '(no summary)'),
    domain,
  };
}