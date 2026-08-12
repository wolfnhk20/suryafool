// src/components/ScanDashboard.js
import { Box, Text, ProgressBar } from 'ink';
import { useState } from '../state/context.js';
import { themes } from '../styles/theme.js';

function ScanDashboard({ theme = 'cyberpunk' }) {
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
              <Text color={t.success}>  ✓ </Text>
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
