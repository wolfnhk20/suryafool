// src/components/InputPrompt.js
// Professional input prompt

import React, { useState } from 'react';
import TextInput from 'ink-text-input';
import { Text, Box } from 'ink';
import { themes } from '../styles/theme.js';

function InputPrompt({ onSubmit, placeholder = 'Type a command...', theme = 'cyberpunk', prompt = '$', disabled = false }) {
  const t = themes[theme] || themes.cyberpunk;
  const [value, setValue] = useState('');

  const handleSubmit = (input) => {
    if (disabled) return;
    if (input.trim() && onSubmit) {
      onSubmit(input.trim());
    }
    setValue('');
  };

  return (
    <Box flexDirection="row" alignItems="center">
      <Text color={t.primary} bold>{prompt}</Text>
      <Text color={t.textDim}>{' '}</Text>
      <Box flexGrow={1}>
        <TextInput
          value={value}
          onChange={setValue}
          onSubmit={handleSubmit}
          placeholder={placeholder}
          placeholderColor={t.muted}
        />
      </Box>
    </Box>
  );
}

export default InputPrompt;