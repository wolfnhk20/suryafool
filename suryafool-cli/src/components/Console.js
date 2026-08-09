// src/components/Console.js
import React from 'react';
import { Box, Text } from 'ink';
import { useState } from '../state/context.js';

function Console({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', text: '#e0e0ff', muted: '#444466', border: '#1a1a3a', background: '#0a0a1a' },
    clean: { primary: '#4a9eff', text: '#d0d0e0', muted: '#7f8c8d', border: '#3a3a5a', background: '#1e1e2e' },
  };
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();

  return (
    <Box flexGrow={1} flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text color={t.primary} bold>CONSOLE</Text>
      </Box>
      <Box flexGrow={1} borderStyle="single" borderColor={t.border} padding={1}>
        {state.logs.length > 0 ? (
          state.logs.map((log, i) => (
            <Text key={i} color={t.text}>{log}</Text>
          ))
        ) : (
          <Text color={t.muted}>  No output yet</Text>
        )}
      </Box>
    </Box>
  );
}

export default Console;