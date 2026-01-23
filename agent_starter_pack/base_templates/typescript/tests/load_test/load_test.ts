async function runLoadTest() {
  const baseUrl = process.env.STAGING_URL || 'http://localhost:8000';
  const idToken = process.env._ID_TOKEN;

  // Build headers - add auth if token provided (for Cloud Run)
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (idToken) {
    headers['Authorization'] = `Bearer ${idToken}`;
  }

  const numUsers = 5;
  const requestsPerUser = 2;
  let successes = 0;
  let failures = 0;
  const latencies: number[] = [];
  const statusCodes: Record<number, number> = {};

  const startTime = Date.now();
  console.log(`Starting load test: ${numUsers} users, ${requestsPerUser} requests each...`);

  // Run users in parallel, but each user's requests are sequential
  const userPromises = Array.from({ length: numUsers }, async (_, i) => {
    const userId = `load-test-user-${i}`;
    const sessionId = `session-${Date.now()}-${i}`;

    // 1. Create session
    const sessionRes = await fetch(`${baseUrl}/apps/agent/users/${userId}/sessions/${sessionId}`, {
      method: 'POST',
      headers,
      body: '{}',
    });

    if (!sessionRes.ok) {
      console.error(`User ${i}: Failed to create session: ${sessionRes.status}`);
      failures += requestsPerUser;
      return;
    }

    // 2. Send sequential requests
    for (let j = 0; j < requestsPerUser; j++) {
      const reqStart = Date.now();
      const res = await fetch(`${baseUrl}/run`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          appName: 'agent',
          userId,
          sessionId,
          newMessage: { role: 'user', parts: [{ text: `Hello ${j}!` }] },
        }),
      });
      const latency = Date.now() - reqStart;
      latencies.push(latency);
      statusCodes[res.status] = (statusCodes[res.status] || 0) + 1;

      if (res.ok) {
        successes++;
      } else {
        console.error(`User ${i} request ${j}: ${res.status}`);
        failures++;
      }
    }
  });

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

  console.log('\n--- Load Test Results ---');
  console.log(`Duration: ${duration.toFixed(2)}s`);
  console.log(`Requests: ${total} (${successes} succeeded, ${failures} failed)`);
  console.log(`Success rate: ${successRate.toFixed(1)}%`);
  console.log(`Throughput: ${(total / duration).toFixed(2)} req/s`);
  console.log(`\nLatency (ms):`);
  console.log(`  min: ${stats.min}, max: ${stats.max}, avg: ${stats.avg}`);
  console.log(`  p50: ${stats.p50}, p95: ${stats.p95}, p99: ${stats.p99}`);
  console.log(`\nStatus codes:`, statusCodes);

  process.exit(failures === 0 ? 0 : 1);
}

runLoadTest().catch((err) => {
  console.error('Load test failed:', err);
  process.exit(1);
});
