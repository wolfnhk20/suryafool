export default {
  test: {
    globals: true,
    environment: 'node',
  },
  esbuild: {
    loader: 'jsx',
    include: ['**/*.js'],
  },
}