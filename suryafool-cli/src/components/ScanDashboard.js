// src/components/ScanDashboard.js
import { Box, Text, ProgressBar } from 'ink';
import { useState } from '../state/context.js';

function ScanDashboard({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', text: '#e0e0ff', muted: '#444466', border: '#1a1a3a', background: '#0a0a1a', success: '#00ff00', error: '#ff0040' },
    clean: { primary: '#4a9eff', text: '#d0d0e0', muted: '#7f8c8d', border: '#3a3a5a', background: '#1e1e2e', success: '#2ecc71', error: '#e74c3c' },
  };
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();

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
              <Text color={t.success}>  � ✓ </Text>
              <Text color={t.text}>{f}</Text>
            </Box>
          ))
        ) : (
          <Text color={t.muted}>  No findings yet</Text>
        )}
        <Box marginTop={1}>
          <Text color={t.text}>PROGRESS:</Text>
          <ProgressBar 
            value={state.dashboard?.progress || 0} 
            width={30} 
            completedColor={t.success} 
            uncompletedColor={t.border} 
          />
        </Box>
      </Box>
    </Box>
  );
}

export default ScanDashboard;