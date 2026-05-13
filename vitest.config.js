import { defineConfig } from 'vitest/config';

// Nota: as funções puras de analise.js vivem dentro de index.html e são
// extraídas via eval() em tests/js/helpers/extract-analise.js. Por isso,
// coverage v8 só mede o helper, não o código real — thresholds seriam
// enganosos. O `npm run test:js:coverage` ainda dá um relatório útil
// para inspecionar visualmente paths não exercitados no próprio helper.
export default defineConfig({
  test: {
    include: ['tests/js/**/*.test.js'],
    environment: 'node',
    testTimeout: 10000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
    },
  },
});
