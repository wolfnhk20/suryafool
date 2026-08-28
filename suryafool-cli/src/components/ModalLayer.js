// src/components/ModalLayer.js
import React from 'react';
import { Box, Text } from 'ink';
import { useState, useDispatch } from '../state/context.js';
import { themes } from '../styles/theme.js';

function ModalLayer({ theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const state = useState();
  const dispatch = useDispatch();
  const modal = state.modal;

  if (!modal) return null;

  const handleClose = () => {
    dispatch({ type: 'CLEAR_MODAL' });
  };

  const titleColor = modal.type === 'error' ? t.error : modal.type === 'warning' ? t.warning : t.primary;

  return (
    <Box
      position="absolute"
      top="20%"
      left="20%"
      width="60%"
      flexDirection="column"
      paddingX={2}
      paddingY={1}
      borderStyle="round"
      borderColor={titleColor}
      backgroundColor={t.background}
    >
      <Box marginBottom={1}>
        <Text color={titleColor} bold>{modal.title || 'NOTICE'}</Text>
      </Box>
      <Box marginBottom={1}>
        <Text color={t.text}>{modal.message || ''}</Text>
      </Box>
      <Box flexDirection="row" justifyContent="flex-end">
        <Text color={t.primary} bold onClick={handleClose}>[ OK ]</Text>
      </Box>
    </Box>
  );
}

export default ModalLayer;