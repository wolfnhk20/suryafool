// src/components/CommandBar.js
import React from 'react';
import { Box, Text } from 'ink';
import InputPrompt from './InputPrompt.js';
import { themes } from '../styles/theme.js';

function CommandBar({ theme = 'cyberpunk', onCommand, disabled = false, commandStatus = 'idle' }) {
  const t = themes[theme] || themes.cyberpunk;

  return (
    <Box
      flexDirection="row"
      alignItems="center"
      paddingX={2}
      height={3}
      borderStyle="single"
      borderColor={t.border}
    >
      <InputPrompt
        onSubmit={onCommand}
        theme={theme}
        placeholder={disabled ? 'mission in progress...' : 'run mission: scan <target>, explore, agents, doctor, capabilities, scenarios, run, help, exit'}
        disabled={disabled}
      />
    </Box>
  );
}

export default CommandBar;