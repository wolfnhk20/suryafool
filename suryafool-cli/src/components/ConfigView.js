// src/components/ConfigView.js
import React from 'react';
import { Box, Text } from 'ink';
import { useState, useDispatch } from '../state/context.js';
import { themes } from '../styles/theme.js';

function ConfigView({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();
  const dispatch = useDispatch();

  const changeTheme = () => {
    const newTheme = state.theme === 'cyberpunk' ? 'clean' : 'cyberpunk';
    dispatch({ type: 'SET_THEME', payload: newTheme });
  };

  return (
    <Box flexGrow={1} flexDirection="column" padding={1}>
      <Box marginBottom={1}>
        <Text color={t.primary} bold>CONFIGURATION</Text>
      </Box>
      <Box flexGrow={1} flexDirection="column" borderStyle="single" borderColor={t.border} padding={1}>
        <Text color={t.text}>Current theme: {state.theme}</Text>
        <Box marginTop={1}>
          <Text
            color={t.primary}
            backgroundColor={t.border}
            paddingX={2}
            paddingY={1}
            onClick={changeTheme}
          >
            Change Theme
          </Text>
        </Box>
      </Box>
    </Box>
  );
}

export default ConfigView;
