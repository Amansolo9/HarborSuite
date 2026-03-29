import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'python -c "from pathlib import Path; Path(\'e2e.db\').unlink(missing_ok=True)" && python scripts/bootstrap_db.py && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/health',
      cwd: '..',
      reuseExistingServer: true,
      timeout: 120_000,
      env: {
        DATABASE_URL: 'sqlite:///./e2e.db',
        APP_ENV: 'dev',
        SEED_DEMO_DATA: 'true',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173/login',
      cwd: '.',
      reuseExistingServer: true,
      timeout: 120_000,
      env: {
        VITE_API_BASE: 'http://127.0.0.1:8000',
        VITE_SESSION_IDLE_MINUTES: '15',
      },
    },
  ],
})
