// src/components/Console.js
import React from 'react';
import { Box, Text } from 'ink';
import { useState } from '../state/context.js';
import { themes } from '../styles/theme.js';

const MAX_LOGS = 50;

function Console({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();

  const getLogColor = (level) => {
    switch (level) {
      case 'success': return t.success;
      case 'error':   return t.error;
      case 'warning': return t.warning;
      case 'info':    return t.textDim;
      default:        return t.textDim;
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '--:--';
    const d = new Date(timestamp);
    return d.toTimeString().substring(0, 5);
  };

  const formatLog = (log) => {
    if (typeof log === 'string') return log;
    return log?.message || JSON.stringify(log);
  };

  const logs = (state.logs || []).slice(-MAX_LOGS);

  return (
    <Box flexDirection="column" flexGrow={1} width="100%">
      <Box flexDirection="row" paddingX={1} height={3} alignItems="center">
        <Text color={t.textDim} dimColor>MISSION LOG</Text>
      </Box>
      <Box
        flexDirection="column"
        flexGrow={1}
        paddingX={1}
        paddingY={1}
        borderStyle="single"
        borderColor={t.border}
      >
        {logs.length > 0 ? (
          logs.map((log, i) => (
            <Box key={i} flexDirection="row">
              <Text color={t.muted}>{formatTime(log?.timestamp)}  </Text>
              <Text color={getLogColor(log?.level)}>
                {formatLog(log)}
              </Text>
            </Box>
          ))
        ) : (
          <Text color={t.muted}>  No mission activity yet</Text>
        )}
      </Box>
    </Box>
  );
}

export default Console;