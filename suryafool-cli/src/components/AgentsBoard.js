// src/components/AgentsBoard.js
import { Box, Text } from 'ink';
import { useState } from '../state/context.js';
import { themes } from '../styles/theme.js';

function AgentsBoard({ theme = 'cyberpunk' }) {
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
              <Text color={t.accent}>  ► </Text>
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
