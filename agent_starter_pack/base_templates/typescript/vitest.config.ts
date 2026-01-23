import { defineConfig } from 'vitest/config';
import { config } from 'dotenv';

// Load .env from project root before tests run
config();

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    },
  },
});
