// src/styles/theme.js
// Restrained sunflower-inspired palette. Gold primary, amber secondary,
// muted green success, warm white text. Cyan reserved for interaction.

export const themes = {
  cyberpunk: {
    name:         'Cyberpunk',
    primary:      '#E8B339',  // Sunflower gold (brand)
    secondary:    '#D97706',  // Warm amber (status)
    accent:       '#65A30D',  // Muted green (environment/success)
    success:      '#65A30D',  // Muted green
    error:        '#DC2626',  // Restrained red
    warning:      '#D97706',  // Warm amber
    info:         '#0891B2',  // Reserved: cyan info (sparingly used)
    interactive:  '#06B6D4',  // Reserved: active interaction accent
    muted:        '#78716C',  // Warm gray
    subtle:       '#292524',  // Dark warm gray
    background:   '#0C0A09',  // Very dark warm
    surface:      '#1C1917',  // Warm dark surface
    border:       '#44403C',  // Warm dark border
    text:         '#FAFAF9',  // Warm white
    textDim:      '#A8A29E',  // Muted warm
    highlight:    '#FBBF24',  // Bright gold (emphasis moments only)
  },
  clean: {
    name:         'Clean',
    primary:      '#B45309',  // Dark amber-gold (brand)
    secondary:    '#92400E',  // Warm brown-amber
    accent:       '#4D7C0F',  // Muted olive green
    success:      '#4D7C0F',  // Muted olive
    error:        '#B91C1C',  // Restrained red
    warning:      '#B45309',  // Warm amber
    info:         '#0E7490',  // Reserved cyan
    interactive:  '#0E7490',  // Active interaction
    muted:        '#78716C',  // Warm gray
    subtle:       '#F5F5F4',  // Light warm
    background:   '#FAFAF9',  // Warm white
    surface:      '#FFFFFF',  // White
    border:       '#D6D3D1',  // Warm light border
    text:         '#1C1917',  // Dark warm
    textDim:      '#57534E',  // Muted warm dark
    highlight:    '#D97706',  // Bright amber emphasis
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