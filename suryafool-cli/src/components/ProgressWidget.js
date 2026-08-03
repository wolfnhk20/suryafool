// src/components/ProgressWidget.js
// Progress bars and spinners

import React from 'react';
import { Text, Box } from 'ink';
import { themes } from '../styles/theme.js';

function ProgressBar({ progress, width = 30, label = '', theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const filled = Math.floor((progress / 100) * width);
  const empty = width - filled;
  const bar = '█'.repeat(filled) + '░'.repeat(empty);

  return (
    <Box>
      {label && <Text color={t.muted}>{label} </Text>}
      <Text color={t.primary}>[</Text>
      <Text color={progress >= 80 ? themes[theme].success : themes[theme].primary}>{'█'.repeat(Math.floor(progress / 100 * width))}</Text>
      <Text color={themes[theme].muted}>{'░'.repeat(width - Math.floor(progress / 100 * width))}</Text>
      <Text color={themes[theme].primary}>]</Text>
      <Text color={themes[theme].accent}> {Math.floor(progress)}%</Text>
    </Box>
  );
}

function Spinner({ text, style = 'dots', theme = 'cyberpunk' }) {
  const t = themes[theme] || themes.cyberpunk;
  const [frame, setFrame] = React.useState(0);

  const frames = {
    dots: ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
    scan: ['/', '-', '\\', '|'],
    pulse: ['░', '▒', '▓', '█', '▓', '▒', '░'],
    bounce: ['⠁', '⠂', '⠄', '⠂'],
  };

  const framesArray = frames[style] || frames.dots;

  React.useEffect(() => {
    const interval = setInterval(() => {
      setFrame(f => (f + 1) % framesArray.length);
    }, 80);
    return () => clearInterval(interval);
  }, [framesArray]);

  return (
    <Box>
      <Text color={themes[theme].primary}>{framesArray[frame]}</Text>
      <Text color={themes[theme].text}> {text}</Text>
    </Box>
  );
}

export { ProgressBar, Spinner };