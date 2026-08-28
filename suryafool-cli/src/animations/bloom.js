// src/animations/bloom.js
// Non-blocking bloom animation. Cycles through glyph frames for a
// short duration then settles to static. Caller may cancel.

const BLOOM_FRAMES = ['bloom1', 'bloom2', 'bloom3', 'bloom2', 'bloom1', 'static'];
const FRAME_INTERVAL_MS = 100;

export function runBloom(setState, durationMs = 1000) {
  let idx = 0;
  setState(BLOOM_FRAMES[0]);

  const interval = setInterval(() => {
    idx++;
    if (idx >= BLOOM_FRAMES.length) {
      clearInterval(interval);
      setState('static');
      return;
    }
    setState(BLOOM_FRAMES[idx]);
  }, FRAME_INTERVAL_MS);

  // Safety: always settle to static even if frames run short
  const timeout = setTimeout(() => {
    clearInterval(interval);
    setState('static');
  }, durationMs + 100);

  return {
    cancel: () => {
      clearInterval(interval);
      clearTimeout(timeout);
      setState('static');
    },
  };
}
