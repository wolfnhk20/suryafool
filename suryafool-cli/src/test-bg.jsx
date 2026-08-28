import React from 'react';
import { Box, Text } from 'ink';

function Test() {
  return (
    <Box flexDirection="column">
      <Text>Background below this should not show</Text>
      <Box
        position="absolute"
        top="20%"
        left="20%"
        width="60%"
        height={5}
        backgroundColor="#ff0000"
      >
        <Text>INSIDE MODAL</Text>
      </Box>
    </Box>
  );
}

export default Test;
