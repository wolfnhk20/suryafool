// src/components/InputPrompt.js
// Cyberpunk-styled input prompt

import React, { useState } from 'react';
import TextInput from 'ink-text-input';
import { Text, Box } from 'ink';
import { themes } from '../styles/theme.js';

function InputPrompt({ onSubmit, placeholder = 'Enter command...', theme = 'cyberpunk', prefix = '��⚡' }) {
  const t = themes[theme] || themes.cyberpunk;
  const [value, setValue] = useState('');

  const handleSubmit = (input) => {
    if (input.trim() && onSubmit) {
      onSubmit(input.trim());
    }
    setValue('');
  };

  return (
    <Box padding={1}>
      <Text color={t.primary} bold>{prefix} </Text>
      <TextInput
        value={value}
        onChange={setValue}
        onSubmit={handleSubmit}
        placeholder={placeholder}
        placeholderColor={t.muted}
      />
    </Box>
  );
}

export default InputPrompt;