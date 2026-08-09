// src/components/ConfigView.js
import { Box, Text } from 'ink';
import { useState, useDispatch } from '../state/context.js';

function ConfigView({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', text: '#e0e0ff', muted: '#444466', border: '#1a1a3a', background: '#0a0a1a' },
    clean: { primary: '#4a9eff', text: '#d0d0e0', muted: '#7f8c8d', border: '#3a3a5a', background: '#1e1e2e' },
  };
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
      <Box flexGrow={1} borderStyle="single" borderColor={t.border} padding={1}>
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