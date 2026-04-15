/**
 * SmartOps AI – k6 Load Test Suite
 * Tests User → Order → Payment service chain with multiple scenarios.
 *
 * Run:  k6 run k6/load_test.js
 * Env:  BASE_URL=http://localhost:8000 k6 run k6/load_test.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import exec from 'k6/execution';
import { Counter, Rate, Trend } from 'k6/metrics';

// ─── Custom Metrics ──────────────────────────────────────────────────────────
const orderErrors    = new Counter('order_errors_total');
const paymentErrors  = new Counter('payment_errors_total');
const healthErrors   = new Counter('health_check_errors');
const successRate    = new Rate('success_rate');
const orderDuration  = new Trend('order_duration_ms', true);

// ─── Options ─────────────────────────────────────────────────────────────────
export const options = {
  stages: [
    { duration: '30s', target: 10  },   // Warm-up ramp
    { duration: '30s', target: 20  },   // Normal load
    { duration: '30s', target: 50  },   // Spike load (triggers anomalies)
    { duration: '30s', target: 0   },   // Ramp-down
  ],
  thresholds: {
    // Allow 10% failure — services simulate chaos
    http_req_failed:     ['rate<0.1'],
    // 95th percentile request time < 3s
    http_req_duration:   ['p(95)<3000'],
    // At least 80% of orders must succeed
    success_rate:        ['rate>0.8'],
    // Order P95 should stay under 2s
    order_duration_ms:   ['p(95)<2000'],
  },
};

// ─── Config ───────────────────────────────────────────────────────────────────
const BASE_URL         = __ENV.BASE_URL         || 'http://localhost:8000';
const ORDER_URL        = __ENV.ORDER_URL         || 'http://localhost:8001';
const PAYMENT_URL      = __ENV.PAYMENT_URL       || 'http://localhost:8002';
const SMARTOPS_URL     = __ENV.SMARTOPS_URL      || 'http://localhost:9000';

function getHeaders() {
  return {
    'Content-Type':  'application/json',
    'Accept':        'application/json',
    'X-Request-ID':  `k6-${__VU}-${exec.iterationInInstance}`,
  };
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function randUser()   { return Math.floor(Math.random() * 1000) + 1; }
function randAmount() { return parseFloat((Math.random() * 200 + 10).toFixed(2)); }

// ─── Main Scenario ────────────────────────────────────────────────────────────
export default function () {
  const userId = randUser();
  const amount = randAmount();

  group('Health Checks', () => {
    const checks = [
      { name: 'user-svc',    url: `${BASE_URL}/health` },
      { name: 'order-svc',   url: `${ORDER_URL}/health` },
      { name: 'payment-svc', url: `${PAYMENT_URL}/health` },
    ];
    checks.forEach(c => {
      const r = http.get(c.url, { headers: getHeaders(), tags: { service: c.name } });
      const ok = check(r, { [`${c.name} healthy`]: res => res.status === 200 });
      if (!ok) healthErrors.add(1);
    });
  });

  group('Register Order (Full Chain)', () => {
    const payload = JSON.stringify({ user_id: userId, amount });
    const start = Date.now();

    const res = http.post(
      `${BASE_URL}/register_order`,
      payload,
      { headers: getHeaders(), timeout: '10s', tags: { type: 'order' } }
    );

    const elapsed = Date.now() - start;
    orderDuration.add(elapsed);

    const ok = check(res, {
      'register_order status 200': r => r.status === 200,
      'response has id':           r => { try { return r.json().id !== undefined; } catch { return false; } },
    });

    successRate.add(ok);
    if (!ok) {
      orderErrors.add(1);
      console.warn(`Order failed: VU=${__VU} status=${res.status} body=${res.body.slice(0,200)}`);
    }
  });

  group('Direct Payment Check', () => {
    const r = http.post(
      `${PAYMENT_URL}/process`,
      JSON.stringify({ order_id: Math.floor(Math.random()*9999)+1, amount, user_id: userId }),
      { headers: getHeaders(), tags: { type: 'payment' } }
    );
    const ok = check(r, { 'payment processed': res => res.status === 200 });
    if (!ok) paymentErrors.add(1);
  });

  group('SmartOps Engine Check', () => {
    const r = http.get(`${SMARTOPS_URL}/api/metrics`, { headers: getHeaders() });
    check(r, { 'engine metrics 200': res => res.status === 200 });
  });

  sleep(1);
}

// ─── Setup: report test config ────────────────────────────────────────────────
export function setup() {
  console.log('SmartOps AI – Load Test Starting');
  console.log(`  User Service:    ${BASE_URL}`);
  console.log(`  Order Service:   ${ORDER_URL}`);
  console.log(`  Payment Service: ${PAYMENT_URL}`);
  console.log(`  SmartOps Engine: ${SMARTOPS_URL}`);
  return { startedAt: new Date().toISOString() };
}

// ─── Teardown: summary ────────────────────────────────────────────────────────
export function teardown(data) {
  console.log(`\nLoad test complete. Started: ${data.startedAt}`);
}
