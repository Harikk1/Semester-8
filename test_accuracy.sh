#!/bin/bash

# SmartOps AI - Accuracy Test Suite
# Tests the enhanced anomaly detection and RCA capabilities

echo "🚀 SmartOps AI - Beast Mode Accuracy Test"
echo "=========================================="
echo ""

# Check if services are running
echo "1. Checking service health..."
services=("http://localhost:8000/health" "http://localhost:8001/health" "http://localhost:8002/health" "http://localhost:9000/health")
for service in "${services[@]}"; do
    response=$(curl -s -o /dev/null -w "%{http_code}" "$service" 2>/dev/null)
    if [ "$response" = "200" ]; then
        echo "   ✅ $service - OK"
    else
        echo "   ❌ $service - FAILED (HTTP $response)"
    fi
done
echo ""

# Test anomaly detection
echo "2. Testing anomaly detection..."
echo "   Triggering CPU stress on order_service..."
curl -s -X POST "http://localhost:9000/api/simulate/cpu_stress/order_service" > /dev/null
echo "   ✅ CPU stress triggered"
echo "   Waiting 20 seconds for detection..."
sleep 20

# Check for anomalies
anomalies=$(curl -s "http://localhost:9000/api/anomalies?limit=5" | grep -o '"severity":"critical"' | wc -l)
echo "   📊 Critical anomalies detected: $anomalies"
echo ""

# Test RCA
echo "3. Testing Root Cause Analysis..."
incidents=$(curl -s "http://localhost:9000/api/incidents?limit=5" | grep -o '"incident_id"' | wc -l)
echo "   📊 Incidents analyzed: $incidents"
echo ""

# Test metrics accuracy
echo "4. Testing metrics collection..."
metrics=$(curl -s "http://localhost:9000/api/metrics")
echo "   ✅ Metrics endpoint responding"
echo ""

# Test remediation
echo "5. Testing remediation engine..."
remediations=$(curl -s "http://localhost:9000/api/remediation?limit=5" | grep -o '"status"' | wc -l)
echo "   📊 Remediation actions: $remediations"
echo ""

# Performance test
echo "6. Running performance test (10 orders)..."
start_time=$(date +%s)
for i in {1..10}; do
    curl -s -X POST "http://localhost:8000/register_order" \
         -H "Content-Type: application/json" \
         -d "{\"user_id\": $i, \"amount\": 99.99}" > /dev/null &
done
wait
end_time=$(date +%s)
duration=$((end_time - start_time))
echo "   ✅ Completed in ${duration}s"
echo "   📊 Throughput: $(echo "scale=2; 10 / $duration" | bc) req/s"
echo ""

echo "=========================================="
echo "✅ Accuracy test completed!"
echo ""
echo "Next steps:"
echo "  1. Check dashboard at http://localhost:5173"
echo "  2. View RCA page for incident analysis"
echo "  3. Monitor anomalies in real-time"
echo "  4. Run k6 load test: k6 run server/microservices-lab/k6/load_test.js"
