import { describe, it, expect, beforeEach } from 'vitest';
import { Runner, InMemorySessionService } from '@google/adk';
import { rootAgent } from '../../{{cookiecutter.agent_directory}}/agent.js';

describe('Agent Integration', () => {
  let runner: Runner;
  let sessionService: InMemorySessionService;

  beforeEach(() => {
    sessionService = new InMemorySessionService();
    runner = new Runner({
      appName: 'test-app',
      agent: rootAgent,
      sessionService,
    });
  });

  it('should respond to a weather query', async () => {
    await sessionService.createSession({
      appName: 'test-app',
      userId: 'test-user',
      sessionId: 'test-session',
    });

    const events: unknown[] = [];
    for await (const event of runner.runAsync({
      userId: 'test-user',
      sessionId: 'test-session',
      newMessage: {
        role: 'user',
        parts: [{ text: 'What is the weather in San Francisco?' }],
      },
    })) {
      events.push(event);
    }

    expect(events.length).toBeGreaterThan(0);
    // Assert that we got events back from the agent
    expect(events.some(e => (e as { content?: unknown }).content)).toBe(true);
  });

  it('should respond to another weather query', async () => {
    await sessionService.createSession({
      appName: 'test-app',
      userId: 'test-user',
      sessionId: 'test-session-2',
    });

    const events: unknown[] = [];
    for await (const event of runner.runAsync({
      userId: 'test-user',
      sessionId: 'test-session-2',
      newMessage: {
        role: 'user',
        parts: [{ text: 'What is the weather in New York?' }],
      },
    })) {
      events.push(event);
    }

    expect(events.length).toBeGreaterThan(0);
  });
});
