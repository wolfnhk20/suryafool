// src/styles/theme.js
// Cyberpunk and Clean theme definitions

export const themes = {
  cyberpunk: {
    primary:      '#00ffff',  // Cyan neon
    secondary:    '#ff00ff',  // Magenta
    accent:       '#ffff00',  // Yellow warning
    success:      '#00ff41',  // Matrix green
    error:        '#ff0040',  // Neon red
    warning:      '#ffaa00',  // Orange
    muted:        '#444466',  // Dim purple-gray
    background:   '#0a0a1a',  // Deep dark
    border:       '#1a1a3a',  // Subtle border
    text:         '#e0e0ff',  // Light blue-white
    highlight:    '#ff6600',  // Orange highlight
    glow:         'cyan',     // Glow color for effects
  },
  clean: {
    primary:      '#4a9eff',  // Blue
    secondary:    '#9b59b6',  // Purple
    accent:       '#f39c12',  // Amber
    success:      '#2ecc71',  // Green
    error:        '#e74c3c',  // Red
    warning:      '#f39c12',  // Amber
    muted:        '#7f8c8d',  // Gray
    background:   '#1e1e2e',  // Dark
    border:       '#3a3a5a',  // Border
    text:         '#d0d0e0',  // Light
    highlight:    '#e67e22',  // Orange
    glow:         'blue',     // Glow
  }
};

export function getTheme(name) {
  return themes[name] || themes.cyberpunk;
}

export function applyTheme(theme, chalk) {
  const themedChalk = {};
  
  Object.keys(chalk).forEach(key => {
    if (typeof chalk[key] === 'function') {
      themedChalk[key] = chalk[key];
    }
  });

  themedChalk.cyberPrimary = chalk.hex(theme.primary);
  themedChalk.cyberSecondary = chalk.hex(theme.secondary);
  themedChalk.cyberAccent = chalk.hex(theme.accent);
  themedChalk.cyberSuccess = chalk.hex(theme.success);
  themedChalk.cyberError = chalk.hex(theme.error);
  themedChalk.cyberWarning = chalk.hex(theme.warning);
  themedChalk.cyberMuted = chalk.hex(theme.muted);
  themedChalk.cyberBorder = chalk.hex(theme.border);
  themedChalk.cyberText = chalk.hex(theme.text);
  themedChalk.cyberHighlight = chalk.hex(theme.highlight);

  return themedChalk;
}