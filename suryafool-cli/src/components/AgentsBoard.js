// src/components/AgentsBoard.js
import { Box, Text } from 'ink';
import { useState } from '../state/context.js';

function AgentsBoard({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', text: '#e0e0ff', muted: '#444466', border: '#1a1a3a', background: '#0a0a1a', accent: '#ff00ff' },
    clean: { primary: '#4a9eff', text: '#d0d0e0', muted: '#7f8c8d', border: '#3a3a5a', background: '#1e1e2e', accent: '#9b59b6' },
  };
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();

  return (
    <Box flexGrow={1} flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text color={t.primary} bold>AGENTS BOARD</Text>
      </Box>
      <Box flexGrow={1} borderStyle="single" borderColor={t.border} padding={1}>
        <Text color={t.text} marginBottom={1}>ACTIVE AGENTS:</Text>
        {state.agents?.length > 0 ? (
          state.agents.map((agent, i) => (
            <Box key={i} flexDirection="row" marginBottom={0.5}>
              <Text color={t.accent}>  � ► </Text>
              <Text color={t.text}>{agent}</Text>
            </Box>
          ))
        ) : (
          <Text color={t.muted}>  No active agents</Text>
        )}
      </Box>
    </Box>
  );
}

export default AgentsBoard;