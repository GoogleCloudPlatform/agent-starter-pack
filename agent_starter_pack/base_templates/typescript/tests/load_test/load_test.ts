async function runLoadTest() {
  const baseUrl = process.env.STAGING_URL || 'http://localhost:8000';
  const idToken = process.env._ID_TOKEN;

  const durationSeconds = 30;
  const numUsers = 10;
  const rampRate = 0.5; // users per second

  // Build headers - add auth if token provided (for Cloud Run)
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }

  let successes = 0;
  let failures = 0;
  const latencies: number[] = [];
  const statusCodes: Record<number, number> = {};
  const errors: string[] = [];

  const startTime = Date.now();
  const endTime = startTime + durationSeconds * 1000;
  console.log(`Starting load test: ${numUsers} users, ${durationSeconds}s duration, ${rampRate} users/sec ramp...`);

  // Run users with ramp-up, each user sends requests continuously until duration expires
  const rampIntervalMs = 1000 / rampRate;
  const userPromises: Promise<void>[] = [];

  for (let i = 0; i < numUsers; i++) {
    userPromises.push(runUser(i, baseUrl, headers, endTime, latencies, statusCodes, errors, () => successes++, () => failures++));
    if (i < numUsers - 1) {
      await sleep(rampIntervalMs);
    }
  }

  await Promise.all(userPromises);

  const duration = (Date.now() - startTime) / 1000;
  const total = successes + failures;
  const successRate = total > 0 ? (successes / total) * 100 : 0;

  // Calculate latency stats
  latencies.sort((a, b) => a - b);
  const stats = {
    min: latencies[0] || 0,
    max: latencies[latencies.length - 1] || 0,
    avg: latencies.length > 0 ? Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length) : 0,
    p50: latencies[Math.floor(latencies.length * 0.5)] || 0,
    p95: latencies[Math.floor(latencies.length * 0.95)] || 0,
    p99: latencies[Math.floor(latencies.length * 0.99)] || 0,
  };

  console.log('\n═══════════════════════════════════════════════════════════════');
  console.log('  LOAD TEST RESULTS');
  console.log('═══════════════════════════════════════════════════════════════');
  console.log(`  Duration:       ${duration.toFixed(2)}s`);
  console.log('');
  console.log('  REQUESTS');
  console.log('  ─────────────────────────────────────────────────────────────');
  console.log(`  Total:          ${total}`);
  console.log(`  Successful:     ${successes} (${successRate.toFixed(1)}%)`);
  console.log(`  Failed:         ${failures}`);
  console.log(`  Throughput:     ${(total / duration).toFixed(2)} req/s`);
  console.log('');
  console.log('  LATENCY (ms)');
  console.log('  ─────────────────────────────────────────────────────────────');
  console.log(`  Min:            ${stats.min}`);
  console.log(`  Avg:            ${stats.avg}`);
  console.log(`  Max:            ${stats.max}`);
  console.log(`  P50:            ${stats.p50}`);
  console.log(`  P95:            ${stats.p95}`);
  console.log(`  P99:            ${stats.p99}`);
  console.log('═══════════════════════════════════════════════════════════════');
  console.log(`\nStatus codes:`, statusCodes);

  if (errors.length > 0) {
    console.log('\n  ERRORS (first 5)');
    console.log('  ─────────────────────────────────────────────────────────────');
    for (let i = 0; i < Math.min(5, errors.length); i++) {
      console.log(`  ${i + 1}. ${errors[i]}`);
    }
    if (errors.length > 5) {
      console.log(`  ... and ${errors.length - 5} more errors`);
    }
  }

  const failureRate = total > 0 ? failures / total : 0;
  process.exit(failureRate <= 0.1 ? 0 : 1);
}

async function runUser(
  userNum: number,
  baseUrl: string,
  headers: Record<string, string>,
  endTime: number,
  latencies: number[],
  statusCodes: Record<number, number>,
  errors: string[],
  onSuccess: () => void,
  onFailure: () => void,
) {
  const userId = `load-test-user-${userNum}`;
  const sessionId = `session-${Date.now()}-${userNum}`;

  // 1. Create a session per user
  try {
    const sessionRes = await fetch(`${baseUrl}/apps/agent/users/${userId}/sessions/${sessionId}`, {
      method: 'POST',
      headers,
      body: '{}',
    });

    if (!sessionRes.ok) {
      const body = await sessionRes.text().catch(() => '');
      errors.push(`User ${userNum}: Failed to create session: ${sessionRes.status} - ${body.slice(0, 300)}`);
      onFailure();
      return;
    }
  } catch (err) {
    errors.push(`User ${userNum}: Session creation error: ${err}`);
    onFailure();
    return;
  }

  // 2. Send requests continuously
  while (Date.now() < endTime) {
    const reqStart = Date.now();
    try {
      const res = await fetch(`${baseUrl}/run`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          appName: 'agent',
          userId,
          sessionId,
          newMessage: { role: 'user', parts: [{ text: 'Hello! Weather in New York?' }] },
        }),
      });
      const latency = Date.now() - reqStart;
      latencies.push(latency);
      statusCodes[res.status] = (statusCodes[res.status] || 0) + 1;

      if (res.ok) {
        onSuccess();
      } else {
        const body = await res.text().catch(() => '');
        errors.push(`User ${userNum}: ${res.status} - ${body.slice(0, 300)}`);
        onFailure();
      }
    } catch (err) {
      const latency = Date.now() - reqStart;
      latencies.push(latency);
      errors.push(`User ${userNum}: Request error: ${err}`);
      onFailure();
    }

    // Wait 1-3 seconds between requests
    await sleep(1000 + Math.random() * 2000);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

runLoadTest().catch((err) => {
  console.error('Load test failed:', err);
  process.exit(1);
});
