// src/components/ScanDashboard.js
import React from 'react';
import { Box, Text } from 'ink';
import { useState } from '../state/context.js';
import { themes } from '../styles/theme.js';

function ScanDashboard({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();

  const progress = Math.max(0, Math.min(100, state.dashboard?.progress || 0));
  const width = 30;
  const filled = Math.round((progress / 100) * width);
  const empty = width - filled;

  return (
    <Box flexGrow={1} flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text color={t.primary} bold>SCAN DASHBOARD</Text>
      </Box>
      <Box flexGrow={1} borderStyle="single" borderColor={t.border} padding={1}>
        <Text color={t.text} marginBottom={1}>FINDINGS:</Text>
        {state.dashboard?.findings?.length > 0 ? (
          state.dashboard.findings.map((f, i) => (
            <Box key={i} flexDirection="row" marginBottom={0.5}>
              <Text color={t.success}>  ✓ </Text>
              <Text color={t.text}>{f}</Text>
            </Box>
          ))
        ) : (
          <Text color={t.muted}>  No findings yet</Text>
        )}
        <Box marginTop={1}>
          <Text color={t.text}>PROGRESS: </Text>
          <Text color={t.success}>{'█'.repeat(filled)}</Text>
          <Text color={t.border}>{'░'.repeat(empty)}</Text>
          <Text color={t.text}> {String(progress).padStart(3, ' ')}%</Text>
        </Box>
      </Box>
    </Box>
  );
}

export default ScanDashboard;
