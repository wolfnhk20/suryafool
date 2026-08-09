export default {
  test: {
    globals: true,
    environment: 'node',
    oxc: false,
  },
  esbuild: {
    loader: 'jsx',
    include: ['**/*.js', '**/*.jsx'],
  },
};
