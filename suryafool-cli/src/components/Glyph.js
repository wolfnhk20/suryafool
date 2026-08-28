// src/components/Glyph.js
// Reusable Suryafool sun/flower glyph.
// Terminal-safe characters only. No emoji dependency.

import React from 'react';
import { Text } from 'ink';

export const GLYPH_FRAMES = {
  static:  '*',     // Default resting state — sun point
  bloom1:  '+',     // Opening frame
  bloom2:  '✻',     // Mid-bloom — flower mark (Unicode U+273B)
  bloom3:  '❋',     // Full bloom — heavy flower mark (U+274B)
  pulse:   '·',     // Soft pulse dot
};

export function Glyph({ state = 'static', color }) {
  const ch = GLYPH_FRAMES[state] || GLYPH_FRAMES.static;
  return <Text color={color}>{ch}</Text>;
}

export default Glyph;
