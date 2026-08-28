// src/components/Header.js
import React from 'react';
import { Box, Text } from 'ink';
import { themes } from '../styles/theme.js';
import Glyph from './Glyph.js';

function Header({ theme = 'cyberpunk', commandStatus = 'idle', glyphState = 'static' }) {
  const t = themes[theme] || themes.cyberpunk;

  const statusColor = {
    idle:      t.muted,
    running:   t.warning,
    completed: t.success,
    failed:    t.error,
  }[commandStatus] || t.muted;

  const statusLabel = {
    idle:      'READY',
    running:   'ACTIVE',
    completed: 'COMPLETE',
    failed:    'ERROR',
  }[commandStatus] || 'READY';

  return (
    <Box
      flexDirection="row"
      justifyContent="space-between"
      alignItems="center"
      paddingX={2}
      height={3}
      borderStyle="single"
      borderColor={t.border}
    >
      <Box flexDirection="row" alignItems="center">
        <Glyph state={glyphState} color={t.primary} />
        <Text color={t.text}>  SURYAFOOL</Text>
        <Text color={t.textDim}>   Universal Agentic Wireless Platform</Text>
      </Box>
      <Box flexDirection="row" alignItems="center">
        <Text color={t.textDim}>v0.1.0   </Text>
        <Text color={statusColor} bold>[ {statusLabel} ]</Text>
      </Box>
    </Box>
  );
}

export default Header;