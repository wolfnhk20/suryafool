// src/components/ModalLayer.js
import React from 'react';
import { Box, Text } from 'ink';
import { useState, useDispatch } from '../state/context.js';

function ModalLayer({ theme = 'cyberpunk' }) {
  const themes = {
    cyberpunk: { primary: '#00ffff', text: '#e0e0ff', muted: '#444466', border: '#1a1a3a', background: '#0a0a1a', error: '#ff0040' },
    clean: { primary: '#4a9eff', text: '#d0d0e0', muted: '#7f8c8d', border: '#3a3a5a', background: '#1e1e2e', error: '#e74c3c' },
  };
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();
  const dispatch = useDispatch();
  const modal = state.modal;

  if (!modal) return null;

  const handleClose = () => {
    dispatch({ type: 'CLEAR_MODAL' });
  };

  return (
    <Box
      position="absolute"
      top="20%"
      left="20%"
      width="60%"
      flexDirection="column"
      padding={2}
      backgroundColor={t.background}
    >
      <Text color={modal.type === 'error' ? t.error : t.primary} bold marginBottom={1}>
        {modal.title || 'MODAL'}
      </Text>
      <Text color={t.text} marginBottom={2}>{modal.message || ''}</Text>
      <Box flexDirection="row" justifyContent="flex-end">
        <Text
          color={t.primary}
          backgroundColor={t.border}
          paddingX={2}
          paddingY={1}
          onClick={handleClose}
        >
          OK
        </Text>
      </Box>
    </Box>
  );
}

export default ModalLayer;