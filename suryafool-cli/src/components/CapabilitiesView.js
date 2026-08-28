// src/components/CapabilitiesView.js
// Phase 2 panel: lists capabilities + last run summary by calling the Python
// backend in --json mode and rendering the result.
//
// Pure read-only display — keeps the existing TUI layout untouched.

import React, { useEffect, useState } from 'react';
import { Box, Text } from 'ink';
import { themes } from '../styles/theme.js';
import { getRepoRoot } from '../utils/repo-root.js';

function CapabilitiesView({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const { spawn } = require('child_process');
    const proc = spawn('python', ['-m', 'cli.phase2', 'capabilities', '--json'], {
      cwd: getRepoRoot(),
    });
    let out = '';
    proc.stdout.on('data', (chunk) => { out += chunk.toString(); });
    proc.on('close', (code) => {
      if (cancelled) return;
      try {
        const parsed = JSON.parse(out || '[]');
        setData(parsed);
      } catch (err) {
        setError(`Failed to parse capabilities output: ${err.message}`);
      }
    });
    proc.on('error', (err) => setError(err.message));
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return (
      <Box flexGrow={1} flexDirection="column" padding={1}>
        <Text color={t.error}>CAPABILITIES (error): {error}</Text>
      </Box>
    );
  }
  if (!data) {
    return (
      <Box flexGrow={1} flexDirection="column" padding={1}>
        <Text color={t.primary} bold>CAPABILITIES</Text>
        <Text color={t.muted}>  Loading...</Text>
      </Box>
    );
  }

  return (
    <Box flexGrow={1} flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text color={t.primary} bold>CAPABILITIES</Text>
      </Box>
      <Box flexDirection="column" borderStyle="single" borderColor={t.border} padding={1}>
        {data.map((c, i) => (
          <Box key={i} flexDirection="row" marginBottom={0}>
            <Text color={t.accent}>  ▸ </Text>
            <Text color={t.text}>{c.name.padEnd(22)} </Text>
            <Text color={t.textDim}>{c.key.padEnd(30)} </Text>
            <Text color={c.risk === 'passive' ? t.success : t.warning}>[{c.risk}]</Text>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export default CapabilitiesView;
