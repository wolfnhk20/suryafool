// src/components/EvidenceFeed.js
// Phase 2.7.8 — live evidence feed. Renders the evidence records collected
// from the `evidence.created` JSONL event stream (both Wi-Fi and BLE
// captures) using the existing cyberpunk visual language. Compact by
// default: kind, target, source capability/action, one-line summary.
// Raw `metadata` is intentionally NOT dumped; nothing is derived from it.

import React from 'react';
import { Box, Text } from 'ink';
import { useState } from '../state/context.js';
import { themes } from '../styles/theme.js';
import { formatEvidenceLine } from './evidenceFormat.js';

function EvidenceFeed({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const appState = useState();
  const items = Array.isArray(appState.evidence) ? appState.evidence : [];

  return (
    <Box flexDirection="column" flexGrow={1} padding={1}>
      <Box marginBottom={1}>
        <Text color={t.primary} bold>EVIDENCE FEED</Text>
      </Box>
      {items.length === 0 ? (
        <Text color={t.muted}>  No evidence captured yet.</Text>
      ) : (
        <Box flexDirection="column" borderStyle="single" borderColor={t.border} padding={1}>
          {items.map((rec, i) => {
            const line = formatEvidenceLine(rec);
            const kindColor = line.domain === 'wifi' ? t.primary
              : (line.domain === 'ble' ? t.accent : t.muted);
            return (
              <Box key={i} flexDirection="column" marginBottom={1}>
                <Box flexDirection="row">
                  <Text color={t.accent}>  ▸ </Text>
                  <Text color={kindColor} bold>{line.kind}</Text>
                  <Text color={t.textDim}>  target: </Text>
                  <Text color={t.text}>{line.target}</Text>
                </Box>
                <Box paddingLeft={2}>
                  <Text color={t.textDim}>{line.source}</Text>
                  <Text color={t.text}> — {line.summary}</Text>
                </Box>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
}

export default EvidenceFeed;