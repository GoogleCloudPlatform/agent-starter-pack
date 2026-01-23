import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { spawn, ChildProcess } from 'child_process';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const rootDir = resolve(__dirname, '../..');

async function waitForServer(url: string, maxRetries = 60): Promise<boolean> {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        // Wait until apps are loaded
        if (Array.isArray(data) && data.length > 0) {
          return true;
        }
      }
    } catch {
      // Server not ready yet
    }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  return false;
}

describe('Server E2E', () => {
  let serverProcess: ChildProcess;
  const baseUrl = 'http://localhost:8000';

  beforeAll(async () => {
    // Pass agent.ts directly to avoid bundling test dependencies
    serverProcess = spawn('npx', ['@google/adk-devtools', 'api_server', '{{cookiecutter.agent_directory}}/agent.ts', '--port', '8000'], {
      cwd: rootDir,
      env: { ...process.env },
      stdio: 'pipe',
    });

    // Wait for server to be ready with retries
    const ready = await waitForServer(`${baseUrl}/list-apps`);
    if (!ready) throw new Error('Server failed to start');
  }, 30000);

  afterAll(() => {
    serverProcess?.kill();
  });

  it('should create a session', async () => {
    // App name is "agent" (filename without extension)
    const response = await fetch(
      `${baseUrl}/apps/agent/users/u_123/sessions/s_123`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }
    );
    expect(response.ok).toBe(true);
  });

  it('should run agent via /run endpoint', async () => {
    const response = await fetch(`${baseUrl}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        appName: 'agent',
        userId: 'u_123',
        sessionId: 's_123',
        newMessage: {
          role: 'user',
          parts: [{ text: 'What time is it in San Francisco?' }],
        },
      }),
    });
    if (!response.ok) {
      console.log('Run endpoint failed:', response.status, await response.text());
    }
    expect(response.ok).toBe(true);
    const events = await response.json();
    expect(events.length).toBeGreaterThan(0);
  }, 30000);
});
