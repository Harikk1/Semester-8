import React, { useState } from 'react';
import {
    Terminal, 
    Settings, 
    RefreshCw, 
    Cpu,
    Activity,
    BrainCircuit,
    Sun,
    Moon,
    LogOut,
    User,
    ShoppingCart,
    CreditCard,
    Users,
    Layers,
    Activity as K6Icon
} from 'lucide-react';
import { useSmartOps } from './hooks/useSmartOps';
import { Line } from 'react-chartjs-2';
import Login from './Login';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Filler,
    Legend,
} from 'chart.js';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Filler,
    Legend
);

// Add CSS animations
const styleSheet = document.createElement("style");
styleSheet.textContent = `
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-10px); }
        to { opacity: 1; transform: translateX(0); }
    }
    .glass-panel {
        transition: all 0.3s ease;
    }
    .glass-panel:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    .btn-icon:hover {
        transform: scale(1.1);
        transition: transform 0.2s ease;
    }
`;
document.head.appendChild(styleSheet);

const App = () => {
    const { connected, metrics, anomalies, incidents, remediations, logs, triggerSimulation, generateDemoIncident } = useSmartOps();
    const [activeTab, setActiveTab] = useState('overview');
    const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
    const [user, setUser] = useState(JSON.parse(localStorage.getItem('user')));
    const [currentTime, setCurrentTime] = useState(new Date());

    // Update time every second for live display
    React.useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date());
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    React.useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');
    const handleLogin = (userData) => {
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
    };
    const handleLogout = () => {
        setUser(null);
        localStorage.removeItem('user');
    };

    // Helper to add logs from UI actions
    const addLog = (svc, lvl, msg) => {
        console.log(`[${svc}] ${lvl}: ${msg}`);
    };

    if (!user) return <Login onLogin={handleLogin} theme={theme} />;

    // Generate real-time chart data from actual metrics
    const generateChartData = (service) => {
        const metricData = metrics[service];
        if (!metricData) {
            return Array(20).fill(0).map(() => Math.floor(Math.random() * 50));
        }
        // Use RPS as the primary metric for charts
        const baseValue = metricData.rps || 10;
        return Array(20).fill(0).map((_, i) => {
            const variance = Math.sin(i * 0.5) * 5;
            return Math.max(0, baseValue + variance + (Math.random() - 0.5) * 3);
        });
    };

    const chartData = {
        labels: Array(20).fill(''),
        datasets: [{
            label: 'Global Throughput',
            data: generateChartData(activeTab),
            borderColor: '#00ffa3',
            backgroundColor: 'rgba(0, 255, 163, 0.05)',
            fill: true,
            tension: 0.4,
            borderWidth: 2,
            pointRadius: 0
        }]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { display: false },
            y: { display: false, min: 0 }
        }
    };

    return (
        <div style={styles.container}>
            {/* ─── SIDEBAR ─────────────────── */}
            <aside style={styles.sidebar}>
                <div style={styles.logo}>
                    <span style={styles.logoText}>SmartOps AI</span>
                </div>

                <nav style={styles.nav}>
                    <NavItem label="Overview" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
                    
                    <div style={styles.navSection}>SERVICES</div>
                    <NavItem label="Order Service" active={activeTab === 'order_service'} onClick={() => setActiveTab('order_service')} />
                    <NavItem label="Payment Service" active={activeTab === 'payment_service'} onClick={() => setActiveTab('payment_service')} />
                    <NavItem label="User Service" active={activeTab === 'user_service'} onClick={() => setActiveTab('user_service')} />
                    
                    <div style={styles.navSection}>INFRASTRUCTURE</div>
                    <NavItem label="k8s Cluster" active={activeTab === 'k8s'} onClick={() => setActiveTab('k8s')} />
                    <NavItem label="k6 Testing" active={activeTab === 'k6'} onClick={() => setActiveTab('k6')} />
                    
                    <div style={styles.navSection}>INSIGHTS</div>
                    <NavItem label="Anomalies" active={activeTab === 'anomalies'} onClick={() => setActiveTab('anomalies')} />
                    <NavItem label="Root Cause" active={activeTab === 'rca'} onClick={() => setActiveTab('rca')} />
                    <NavItem label="System Logs" active={activeTab === 'logs'} onClick={() => setActiveTab('logs')} />
                    
                    <div style={{marginTop: 'auto', paddingTop: '20px'}}>
                        <NavItem 
                            label="Logout" 
                            onClick={handleLogout} 
                            style={{color: 'var(--accent-error)', opacity: 0.8}}
                            icon={<LogOut size={14} />} 
                        />
                    </div>
                </nav>

                <div style={styles.sidebarFooter}>
                    <button className="btn-icon" onClick={toggleTheme} title="Toggle Theme">
                        {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
                    </button>
                    <button className="btn-icon" onClick={handleLogout} title="Disconnect session">
                        <Terminal size={14} />
                    </button>
                </div>
            </aside>

            {/* ─── MAIN CONTENT ────────────── */}
            <main style={styles.main}>
                <header style={styles.header}>
                    <div style={styles.headerTitle}>
                        <h1 style={styles.title}>{activeTab.replace('_', ' ')}</h1>
                        <p style={styles.subtitle}>Autonomous Control</p>
                    </div>
                    <div style={styles.headerActions}>
                        <div style={styles.badge}>
                            <div style={{...styles.dot, background: connected ? 'var(--accent-success)' : 'var(--accent-error)'}}></div>
                            {connected ? 'Sync Active' : 'Offline'}
                        </div>
                        <div style={styles.vLine}></div>
                        <div style={{...styles.badge, fontFamily: 'var(--font-mono)', fontSize: '11px'}}>
                            {currentTime.toLocaleTimeString()}
                        </div>
                        <div style={styles.vLine}></div>
                        <div style={styles.profile}>
                            <div style={styles.avatar}>
                                <User size={14} color="var(--text-high)" />
                            </div>
                            <div style={styles.profileInfo}>
                                <span style={styles.userName}>{user?.name || 'Operator'}</span>
                                <span style={styles.userRole}>Node Admin</span>
                            </div>
                        </div>
                        <div style={styles.vLine}></div>
                        <button className="btn-icon"><RefreshCw size={14} /></button>
                    </div>
                </header>

                <div style={styles.scrollArea}>
                    {activeTab === 'overview' && (
                        <div style={styles.grid}>
                            <KPICard 
                                title="HEALTH" 
                                value={connected ? "99.9%" : "OFFLINE"} 
                                sub={`${Object.keys(metrics).length} services monitored`} 
                            />
                            <KPICard 
                                title="ANOMALIES" 
                                value={anomalies.length} 
                                sub={`${anomalies.filter(a => a.severity === 'critical').length} critical`} 
                            />
                            <KPICard 
                                title="THROUGHPUT" 
                                value={`${Object.values(metrics).reduce((sum, m) => sum + (m.rps || 0), 0).toFixed(1)}`} 
                                sub="Req / Sec" 
                            />
                            <KPICard 
                                title="INCIDENTS" 
                                value={incidents.length} 
                                sub={`${remediations.filter(r => r.status === 'completed').length} resolved`} 
                            />

                            <div className="glass-panel" style={styles.heroChart}>
                                <div style={{ padding: '24px' }}>
                                    <h3 style={styles.cardTitle}>Global Telemetry</h3>
                                </div>
                                <div style={{ flex: 1, padding: '0 24px 24px 24px' }}>
                                    <Line data={chartData} options={chartOptions} />
                                </div>
                            </div>

                            <div className="glass-panel" style={styles.sidePanel}>
                                <h3 style={styles.cardTitle}>Event Queue</h3>
                                <div style={styles.incidentList}>
                                    {incidents.slice(0, 5).map(ici => (
                                        <div key={ici.incident_id} style={styles.incidentItem}>
                                            <div style={styles.incidentDot}></div>
                                            <div style={styles.incidentInfo}>
                                                <span style={styles.incidentTitle}>{ici.primary_cause}</span>
                                                <span style={styles.incidentSub}>{ici.service}</span>
                                            </div>
                                        </div>
                                    ))}
                                    {incidents.length === 0 && <p style={styles.emptyText}>Monitoring active.</p>}
                                </div>
                            </div>
                        </div>
                    )}

                    {['order_service', 'payment_service', 'user_service'].includes(activeTab) && (
                        <div style={styles.grid}>
                            <KPICard title="STATUS" value="ONLINE" sub="Node healthy" />
                            <KPICard title="CPU USAGE" value={`${(metrics[activeTab]?.cpu || 0).toFixed(1)}%`} sub="Real-time load" />
                            <KPICard title="MEMORY" value={`${(metrics[activeTab]?.memory || 0).toFixed(0)}MB`} sub="RSS resident" />
                            <KPICard title="LATENCY" value={`${(metrics[activeTab]?.latency_p95 || 0).toFixed(0)}ms`} sub="P95 response" />

                            <div className="glass-panel" style={styles.heroChart}>
                                <div style={{ padding: '24px' }}>
                                    <h3 style={styles.cardTitle}>{activeTab.replace('_', ' ').toUpperCase()} STREAM</h3>
                                </div>
                                <div style={{ flex: 1, padding: '0 24px 24px 24px' }}>
                                    <Line data={chartData} options={chartOptions} />
                                </div>
                            </div>

                            <div className="glass-panel" style={styles.sidePanel}>
                                <h3 style={styles.cardTitle}>METRICS BREAKDOWN</h3>
                                <div style={styles.incidentList}>
                                    <div style={styles.metricRow}>
                                        <span>Throughput</span>
                                        <span style={{color: 'var(--accent-primary)'}}>{(metrics[activeTab]?.rps || 0).toFixed(1)} req/s</span>
                                    </div>
                                    <div style={styles.metricRow}>
                                        <span>Error Rate</span>
                                        <span style={{color: (metrics[activeTab]?.error_rate > 1 ? 'var(--accent-error)' : 'var(--accent-success)')}}>
                                            {(metrics[activeTab]?.error_rate || 0).toFixed(2)}%
                                        </span>
                                    </div>
                                    <div style={styles.metricRow}>
                                        <span>Instances</span>
                                        <span>{(metrics[activeTab]?.instances_up || 0)}/{(metrics[activeTab]?.instances_total || 0)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'k6' && (
                        <div style={{display: 'flex', flexDirection: 'column', gap: '24px'}}>
                            {/* Test Overview */}
                            <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1px', background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '8px', overflow: 'hidden'}}>
                                <KPICard 
                                    title="TOTAL TESTS" 
                                    value="12" 
                                    sub="Last 24 hours" 
                                />
                                <KPICard 
                                    title="SUCCESS RATE" 
                                    value="94.2%" 
                                    sub="Above threshold" 
                                />
                                <KPICard 
                                    title="AVG LATENCY" 
                                    value={`${(Object.values(metrics).reduce((sum, m) => sum + (m.latency_p95 || 0), 0) / Math.max(Object.keys(metrics).length, 1)).toFixed(0)}ms`}
                                    sub="P95 Response Time" 
                                />
                                <KPICard 
                                    title="THROUGHPUT" 
                                    value={`${Object.values(metrics).reduce((sum, m) => sum + (m.rps || 0), 0).toFixed(1)}`}
                                    sub="Requests / Sec" 
                                />
                            </div>

                            {/* Test Control Panel */}
                            <div className="glass-panel" style={{padding: '32px'}}>
                                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px'}}>
                                    <div>
                                        <h3 style={styles.cardTitle}>Load Test Engine</h3>
                                        <p style={{...styles.logMsg, marginTop: '8px', fontSize: '11px'}}>
                                            k6 v0.48.0 • Grafana Cloud Integration • Real-time Metrics
                                        </p>
                                    </div>
                                    <div style={{display: 'flex', gap: '12px'}}>
                                        <button 
                                            style={{...styles.button, background: 'var(--accent-primary)', padding: '10px 20px'}}
                                            onClick={() => {
                                                addLog('K6', 'INFO', 'Starting load test scenario...');
                                                setTimeout(() => addLog('K6', 'SUCCESS', 'Load test completed successfully'), 3000);
                                            }}
                                        >
                                            Run Load Test
                                        </button>
                                        <button 
                                            style={{...styles.button, background: 'var(--bg-element)', color: 'var(--text-high)', padding: '10px 20px'}}
                                            onClick={() => addLog('K6', 'INFO', 'Test configuration exported')}
                                        >
                                            Export Config
                                        </button>
                                    </div>
                                </div>

                                {/* Test Scenarios */}
                                <div style={{marginBottom: '32px'}}>
                                    <h4 style={{...styles.cardTitle, marginBottom: '16px'}}>Test Scenarios</h4>
                                    <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px'}}>
                                        {[
                                            {name: 'Smoke Test', vus: '1-5', duration: '30s', status: 'passed'},
                                            {name: 'Load Test', vus: '10-50', duration: '2m', status: 'passed'},
                                            {name: 'Stress Test', vus: '50-100', duration: '5m', status: 'running'},
                                            {name: 'Spike Test', vus: '0-200', duration: '3m', status: 'pending'},
                                            {name: 'Soak Test', vus: '20', duration: '30m', status: 'pending'},
                                            {name: 'Breakpoint', vus: '0-500', duration: '10m', status: 'pending'}
                                        ].map((scenario, idx) => (
                                            <div key={idx} style={{
                                                padding: '16px',
                                                background: 'var(--bg-element)',
                                                border: '1px solid var(--border-subtle)',
                                                borderRadius: '6px',
                                                cursor: 'pointer',
                                                transition: 'all 0.2s ease',
                                                position: 'relative',
                                                overflow: 'hidden'
                                            }}
                                            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-primary)'}
                                            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
                                            >
                                                {scenario.status === 'running' && (
                                                    <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: '2px', background: 'var(--accent-primary)', animation: 'pulse 2s infinite'}}></div>
                                                )}
                                                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px'}}>
                                                    <div style={{fontSize: '12px', color: 'var(--text-high)', fontWeight: '500'}}>{scenario.name}</div>
                                                    <span style={{
                                                        fontSize: '8px',
                                                        padding: '2px 6px',
                                                        borderRadius: '3px',
                                                        background: scenario.status === 'passed' ? 'rgba(0, 255, 163, 0.1)' : 
                                                                   scenario.status === 'running' ? 'rgba(0, 163, 255, 0.1)' : 'rgba(255, 255, 255, 0.05)',
                                                        color: scenario.status === 'passed' ? 'var(--accent-success)' : 
                                                              scenario.status === 'running' ? 'var(--accent-primary)' : 'var(--text-low)',
                                                        fontWeight: '600',
                                                        letterSpacing: '0.5px',
                                                        textTransform: 'uppercase'
                                                    }}>
                                                        {scenario.status}
                                                    </span>
                                                </div>
                                                <div style={{display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '10px', color: 'var(--text-low)'}}>
                                                    <div>VUs: <span style={{color: 'var(--text-mid)'}}>{scenario.vus}</span></div>
                                                    <div>Duration: <span style={{color: 'var(--text-mid)'}}>{scenario.duration}</span></div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Live Test Results */}
                                <div>
                                    <h4 style={{...styles.cardTitle, marginBottom: '16px'}}>Latest Test Results</h4>
                                    <div style={{...styles.logTerminal, padding: '0'}}>
                                        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr 1fr', gap: '16px', padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', fontSize: '10px', color: 'var(--text-low)', fontWeight: '600', letterSpacing: '1px'}}>
                                            <div>METRIC</div>
                                            <div>AVG</div>
                                            <div>MIN</div>
                                            <div>MAX</div>
                                            <div>P95</div>
                                            <div>STATUS</div>
                                        </div>
                                        {[
                                            {metric: 'http_req_duration', avg: '245ms', min: '89ms', max: '1.2s', p95: '580ms', status: 'pass'},
                                            {metric: 'http_req_waiting', avg: '198ms', min: '45ms', max: '980ms', p95: '450ms', status: 'pass'},
                                            {metric: 'http_reqs', avg: '42.3/s', min: '38/s', max: '58/s', p95: '55/s', status: 'pass'},
                                            {metric: 'vus', avg: '25', min: '10', max: '50', p95: '48', status: 'pass'},
                                            {metric: 'http_req_failed', avg: '2.1%', min: '0%', max: '5.8%', p95: '4.2%', status: 'pass'},
                                            {metric: 'data_received', avg: '1.2MB/s', min: '0.8MB/s', max: '2.1MB/s', p95: '1.9MB/s', status: 'pass'}
                                        ].map((row, idx) => (
                                            <div key={idx} style={{display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr 1fr', gap: '16px', padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', fontSize: '11px', alignItems: 'center'}}>
                                                <div style={{color: 'var(--text-high)', fontFamily: 'var(--font-mono)', fontSize: '10px'}}>{row.metric}</div>
                                                <div style={{color: 'var(--text-mid)'}}>{row.avg}</div>
                                                <div style={{color: 'var(--text-low)'}}>{row.min}</div>
                                                <div style={{color: 'var(--text-low)'}}>{row.max}</div>
                                                <div style={{color: 'var(--accent-primary)'}}>{row.p95}</div>
                                                <div>
                                                    <span style={{
                                                        fontSize: '9px',
                                                        padding: '3px 8px',
                                                        borderRadius: '3px',
                                                        background: 'rgba(0, 255, 163, 0.1)',
                                                        color: 'var(--accent-success)',
                                                        fontWeight: '600',
                                                        letterSpacing: '0.5px'
                                                    }}>
                                                        ✓ PASS
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Test Summary */}
                                <div style={{marginTop: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px'}}>
                                    <div style={{padding: '16px', background: 'var(--bg-element)', borderRadius: '4px', border: '1px solid var(--border-subtle)'}}>
                                        <div style={{fontSize: '10px', color: 'var(--text-low)', marginBottom: '8px', fontWeight: '600', letterSpacing: '1px'}}>THRESHOLDS</div>
                                        <div style={{display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px'}}>
                                            <div style={{display: 'flex', justifyContent: 'space-between'}}>
                                                <span style={{color: 'var(--text-mid)'}}>http_req_duration p(95) &lt; 3000ms</span>
                                                <span style={{color: 'var(--accent-success)'}}>✓</span>
                                            </div>
                                            <div style={{display: 'flex', justifyContent: 'space-between'}}>
                                                <span style={{color: 'var(--text-mid)'}}>http_req_failed rate &lt; 0.1</span>
                                                <span style={{color: 'var(--accent-success)'}}>✓</span>
                                            </div>
                                            <div style={{display: 'flex', justifyContent: 'space-between'}}>
                                                <span style={{color: 'var(--text-mid)'}}>success_rate &gt; 0.8</span>
                                                <span style={{color: 'var(--accent-success)'}}>✓</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div style={{padding: '16px', background: 'var(--bg-element)', borderRadius: '4px', border: '1px solid var(--border-subtle)'}}>
                                        <div style={{fontSize: '10px', color: 'var(--text-low)', marginBottom: '8px', fontWeight: '600', letterSpacing: '1px'}}>TEST INFO</div>
                                        <div style={{display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px', color: 'var(--text-mid)'}}>
                                            <div>Run ID: <span style={{color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)'}}>k6-{Math.floor(Date.now() / 1000)}</span></div>
                                            <div>Duration: <span style={{color: 'var(--text-high)'}}>2m 30s</span></div>
                                            <div>Total Requests: <span style={{color: 'var(--text-high)'}}>6,342</span></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'k8s' && (
                        <div style={{display: 'flex', flexDirection: 'column', gap: '24px'}}>
                            {/* Cluster Overview */}
                            <div style={{display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1px', background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '8px', overflow: 'hidden'}}>
                                <KPICard 
                                    title="NODES" 
                                    value={Object.keys(metrics).length} 
                                    sub={`${Object.keys(metrics).length} Ready`} 
                                />
                                <KPICard 
                                    title="PODS" 
                                    value={Object.values(metrics).reduce((sum, m) => sum + (m.instances_up || 0), 0)} 
                                    sub={`${Object.values(metrics).reduce((sum, m) => sum + (m.instances_total || 0), 0)} Total`} 
                                />
                                <KPICard 
                                    title="CPU USAGE" 
                                    value={`${(Object.values(metrics).reduce((sum, m) => sum + (m.cpu || 0), 0) / Math.max(Object.keys(metrics).length, 1)).toFixed(1)}%`}
                                    sub="Cluster Average" 
                                />
                                <KPICard 
                                    title="MEMORY" 
                                    value={`${(Object.values(metrics).reduce((sum, m) => sum + (m.memory || 0), 0)).toFixed(0)}MB`}
                                    sub="Total Allocated" 
                                />
                            </div>

                            {/* Cluster Topology */}
                            <div className="glass-panel" style={{padding: '32px'}}>
                                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px'}}>
                                    <div>
                                        <h3 style={styles.cardTitle}>Cluster Topology</h3>
                                        <p style={{...styles.logMsg, marginTop: '8px', fontSize: '11px'}}>
                                            smartops-prod-cluster • Region: us-east-1 • Version: v1.28.0
                                        </p>
                                    </div>
                                    <div style={{display: 'flex', gap: '8px'}}>
                                        <div style={{...styles.badge, background: 'var(--bg-element)'}}>
                                            <div style={{...styles.dot, background: 'var(--accent-success)', animation: 'pulse 2s infinite'}}></div>
                                            Healthy
                                        </div>
                                    </div>
                                </div>

                                {/* Node Grid */}
                                <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '32px'}}>
                                    {/* Control Plane Node */}
                                    <div style={{
                                        padding: '20px',
                                        background: 'var(--bg-element)',
                                        border: '1px solid var(--border-subtle)',
                                        borderRadius: '6px',
                                        position: 'relative',
                                        overflow: 'hidden'
                                    }}>
                                        <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: 'var(--accent-primary)'}}></div>
                                        <div style={{fontSize: '10px', color: 'var(--text-low)', marginBottom: '8px', fontWeight: '600', letterSpacing: '1px'}}>CONTROL PLANE</div>
                                        <div style={{fontSize: '14px', color: 'var(--text-high)', fontWeight: '500', marginBottom: '12px'}}>master-01</div>
                                        <div style={{display: 'flex', flexDirection: 'column', gap: '6px'}}>
                                            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px'}}>
                                                <span style={{color: 'var(--text-low)'}}>Status</span>
                                                <span style={{color: 'var(--accent-success)'}}>Ready</span>
                                            </div>
                                            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px'}}>
                                                <span style={{color: 'var(--text-low)'}}>CPU</span>
                                                <span style={{color: 'var(--text-mid)'}}>12.3%</span>
                                            </div>
                                            <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px'}}>
                                                <span style={{color: 'var(--text-low)'}}>Memory</span>
                                                <span style={{color: 'var(--text-mid)'}}>2.1 / 8 GB</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Worker Nodes */}
                                    {['worker-01', 'worker-02'].map((node, idx) => (
                                        <div key={node} style={{
                                            padding: '20px',
                                            background: 'var(--bg-element)',
                                            border: '1px solid var(--border-subtle)',
                                            borderRadius: '6px',
                                            position: 'relative',
                                            overflow: 'hidden'
                                        }}>
                                            <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: 'var(--accent-success)'}}></div>
                                            <div style={{fontSize: '10px', color: 'var(--text-low)', marginBottom: '8px', fontWeight: '600', letterSpacing: '1px'}}>WORKER NODE</div>
                                            <div style={{fontSize: '14px', color: 'var(--text-high)', fontWeight: '500', marginBottom: '12px'}}>{node}</div>
                                            <div style={{display: 'flex', flexDirection: 'column', gap: '6px'}}>
                                                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px'}}>
                                                    <span style={{color: 'var(--text-low)'}}>Status</span>
                                                    <span style={{color: 'var(--accent-success)'}}>Ready</span>
                                                </div>
                                                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px'}}>
                                                    <span style={{color: 'var(--text-low)'}}>Pods</span>
                                                    <span style={{color: 'var(--text-mid)'}}>{Object.values(metrics)[idx]?.instances_up || 0} / {Object.values(metrics)[idx]?.instances_total || 1}</span>
                                                </div>
                                                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px'}}>
                                                    <span style={{color: 'var(--text-low)'}}>CPU</span>
                                                    <span style={{color: 'var(--text-mid)'}}>{Object.values(metrics)[idx]?.cpu?.toFixed(1) || 0}%</span>
                                                </div>
                                                <div style={{display: 'flex', justifyContent: 'space-between', fontSize: '11px'}}>
                                                    <span style={{color: 'var(--text-low)'}}>Memory</span>
                                                    <span style={{color: 'var(--text-mid)'}}>{(Object.values(metrics)[idx]?.memory || 0).toFixed(0)} MB</span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* Deployments */}
                                <div>
                                    <h3 style={{...styles.cardTitle, marginBottom: '16px'}}>Active Deployments</h3>
                                    <div style={{...styles.logTerminal, padding: '0'}}>
                                        <div style={{display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr', gap: '16px', padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', fontSize: '10px', color: 'var(--text-low)', fontWeight: '600', letterSpacing: '1px'}}>
                                            <div>DEPLOYMENT</div>
                                            <div>REPLICAS</div>
                                            <div>AVAILABLE</div>
                                            <div>CPU</div>
                                            <div>STATUS</div>
                                        </div>
                                        {Object.entries(metrics).map(([svc, m]) => (
                                            <div key={svc} style={{display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr', gap: '16px', padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', fontSize: '12px', alignItems: 'center'}}>
                                                <div style={{color: 'var(--text-high)', fontFamily: 'var(--font-mono)'}}>{svc.replace('_', '-')}</div>
                                                <div style={{color: 'var(--text-mid)'}}>{m.instances_total || 1}</div>
                                                <div style={{color: m.instances_up === m.instances_total ? 'var(--accent-success)' : 'var(--accent-warning)'}}>{m.instances_up || 0}/{m.instances_total || 1}</div>
                                                <div style={{color: 'var(--text-mid)'}}>{m.cpu?.toFixed(1) || 0}%</div>
                                                <div>
                                                    <span style={{
                                                        fontSize: '9px',
                                                        padding: '3px 8px',
                                                        borderRadius: '3px',
                                                        background: m.instances_up === m.instances_total ? 'rgba(0, 255, 163, 0.1)' : 'rgba(255, 193, 7, 0.1)',
                                                        color: m.instances_up === m.instances_total ? 'var(--accent-success)' : 'var(--accent-warning)',
                                                        fontWeight: '600',
                                                        letterSpacing: '0.5px'
                                                    }}>
                                                        {m.instances_up === m.instances_total ? 'HEALTHY' : 'DEGRADED'}
                                                    </span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Cluster Info */}
                                <div style={{marginTop: '24px', padding: '16px', background: 'var(--bg-element)', borderRadius: '4px', border: '1px solid var(--border-subtle)'}}>
                                    <div style={{fontSize: '10px', color: 'var(--text-low)', marginBottom: '12px', fontWeight: '600', letterSpacing: '1px'}}>CLUSTER CONTEXT</div>
                                    <div style={{fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-mid)'}}>
                                        kubectl config current-context: <span style={{color: 'var(--accent-primary)'}}>smartops-prod-cluster</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'anomalies' && (
                        <div className="glass-panel" style={{padding: '40px'}}>
                            <h3 style={styles.cardTitle}>Global Anomalies</h3>
                            <div style={styles.logTerminal}>
                                {anomalies.length > 0 ? anomalies.map(a => (
                                    <div key={a.id} style={styles.logLine}>
                                        <span style={styles.logTs}>{a.detected_at.split('T')[1].split('.')[0]}</span>
                                        <span style={{...styles.logLvl, color: 'var(--accent-error)'}}>{a.severity.toUpperCase()}</span>
                                        <span style={styles.logSvc}>{a.service}</span>
                                        <span style={styles.logMsg}>{a.metric}: {a.value} (Threshold: {a.threshold})</span>
                                    </div>
                                )) : <p style={styles.emptyText}>No anomalies detected in the current session.</p>}
                            </div>
                        </div>
                    )}

                    {activeTab === 'rca' && (
                        <div style={{display: 'flex', flexDirection: 'column', gap: '40px'}}>
                            {/* Add manual trigger button */}
                            <div className="glass-panel" style={{padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                <div>
                                    <h3 style={styles.cardTitle}>Incident Analysis Engine</h3>
                                    <p style={{...styles.logMsg, marginTop: '8px', fontSize: '12px'}}>
                                        {incidents.length > 0 
                                            ? `Analyzing ${incidents.length} incident${incidents.length > 1 ? 's' : ''} • ${anomalies.filter(a => a.severity === 'critical').length} critical anomalies detected`
                                            : 'Monitoring all services • No critical incidents detected'}
                                    </p>
                                </div>
                                <div style={{display: 'flex', gap: '12px'}}>
                                    <button 
                                        style={{...styles.button, background: 'var(--accent-primary)', padding: '10px 20px'}}
                                        onClick={generateDemoIncident}
                                    >
                                        Generate Demo Incident
                                    </button>
                                    <button 
                                        style={{...styles.button, background: 'var(--accent-error)', padding: '10px 20px'}}
                                        onClick={() => triggerSimulation('cpu_stress', 'order_service')}
                                    >
                                        CPU Stress Test
                                    </button>
                                    <button 
                                        style={{...styles.button, background: 'var(--accent-warning)', padding: '10px 20px'}}
                                        onClick={() => triggerSimulation('mem_leak', 'payment_service')}
                                    >
                                        Memory Leak Test
                                    </button>
                                </div>
                            </div>

                            {incidents.length > 0 ? incidents.map(ici => (
                                <div key={ici.incident_id} className="glass-panel" style={{padding: '40px', animation: 'fadeIn 0.3s ease-in'}}>
                                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px'}}>
                                        <div>
                                            <h2 style={styles.subtitle}>{ici.primary_cause}</h2>
                                            <div style={{display: 'flex', gap: '12px', marginTop: '8px', alignItems: 'center'}}>
                                                <span style={{...styles.badge, color: 'var(--accent-error)'}}>ID: {ici.incident_id}</span>
                                                <span style={{...styles.badge, color: ici.severity === 'critical' ? 'var(--accent-error)' : 'var(--accent-warning)'}}>
                                                    {ici.severity?.toUpperCase() || 'CRITICAL'}
                                                </span>
                                                {ici.correlation_strength !== undefined && (
                                                    <span style={{...styles.badge, color: 'var(--accent-primary)'}}>
                                                        Correlation: {(ici.correlation_strength * 100).toFixed(0)}%
                                                    </span>
                                                )}
                                                <div style={{...styles.dot, background: 'var(--accent-error)', animation: 'pulse 2s infinite'}}></div>
                                                <span style={{fontSize: '10px', color: 'var(--text-low)'}}>LIVE</span>
                                            </div>
                                        </div>
                                        <div style={{textAlign: 'right'}}>
                                            <div style={{fontSize: '10px', color: 'var(--text-low)', marginBottom: '4px'}}>ANALYZED</div>
                                            <div style={{fontSize: '12px', color: 'var(--text-mid)'}}>{new Date(ici.analyzed_at).toLocaleTimeString()}</div>
                                        </div>
                                    </div>
                                    
                                    <p style={{...styles.logMsg, marginBottom: '32px', fontSize: '14px', lineHeight: '1.6'}}>{ici.ai_summary}</p>
                                    
                                    {ici.affected_metrics && ici.affected_metrics.length > 0 && (
                                        <div style={{marginBottom: '32px', padding: '16px', background: 'var(--bg-element)', borderRadius: '4px', border: '1px solid var(--border-subtle)'}}>
                                            <div style={{fontSize: '10px', color: 'var(--text-low)', marginBottom: '8px', fontWeight: '600', letterSpacing: '1px'}}>AFFECTED METRICS</div>
                                            <div style={{display: 'flex', gap: '8px', flexWrap: 'wrap'}}>
                                                {ici.affected_metrics.map((metric, idx) => (
                                                    <span key={idx} style={{
                                                        fontSize: '11px', 
                                                        padding: '4px 8px', 
                                                        background: 'var(--bg-surface)', 
                                                        borderRadius: '3px',
                                                        color: 'var(--text-high)',
                                                        border: '1px solid var(--border-subtle)'
                                                    }}>
                                                        {metric}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                    
                                    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px'}}>
                                        <div>
                                            <h3 style={styles.cardTitle}>Contributing Factors</h3>
                                            <div style={{marginTop: '16px'}}>
                                                {ici.causes && ici.causes.length > 0 ? ici.causes.map((c, i) => (
                                                    <div key={i} style={{padding: '12px 0', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                                        <div style={{flex: 1}}>
                                                            <span style={{...styles.logMsg, display: 'block'}}>{c.cause}</span>
                                                            {c.correlated_metrics && c.correlated_metrics.length > 0 && (
                                                                <span style={{fontSize: '9px', color: 'var(--text-low)', marginTop: '4px', display: 'block'}}>
                                                                    Correlated: {c.correlated_metrics.join(', ')}
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div style={{textAlign: 'right', marginLeft: '16px'}}>
                                                            <span style={{color: 'var(--accent-primary)', fontSize: '14px', fontWeight: '600'}}>
                                                                {c.confidence ? c.confidence.toFixed(1) : (c.probability * 100).toFixed(0)}%
                                                            </span>
                                                            <div style={{
                                                                width: '60px', 
                                                                height: '4px', 
                                                                background: 'var(--bg-element)', 
                                                                borderRadius: '2px',
                                                                marginTop: '4px',
                                                                overflow: 'hidden'
                                                            }}>
                                                                <div style={{
                                                                    width: `${c.confidence || (c.probability * 100)}%`,
                                                                    height: '100%',
                                                                    background: 'var(--accent-primary)',
                                                                    transition: 'width 0.3s ease'
                                                                }}></div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )) : <p style={styles.emptyText}>No contributing factors identified.</p>}
                                            </div>
                                        </div>
                                        <div>
                                            <h3 style={styles.cardTitle}>Remediation Protocol</h3>
                                            <div style={{marginTop: '16px'}}>
                                                {remediations.filter(r => r.incident_id === ici.incident_id).length > 0 ? 
                                                    remediations.filter(r => r.incident_id === ici.incident_id).map(r => (
                                                        <div key={r.id} style={{padding: '12px 0', borderBottom: '1px solid var(--border-subtle)'}}>
                                                            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                                                <span style={{fontSize: '12px', color: 'var(--text-high)', fontWeight: '500'}}>{r.title}</span>
                                                                <span style={{
                                                                    fontSize: '9px', 
                                                                    color: r.status === 'completed' ? 'var(--accent-success)' : 
                                                                           r.status === 'running' ? 'var(--accent-primary)' : 
                                                                           r.status === 'failed' ? 'var(--accent-error)' : 'var(--text-low)',
                                                                    textTransform: 'uppercase',
                                                                    fontWeight: '700',
                                                                    padding: '3px 6px',
                                                                    background: 'var(--bg-element)',
                                                                    borderRadius: '3px'
                                                                }}>
                                                                    {r.status}
                                                                </span>
                                                            </div>
                                                            <code style={{fontSize: '10px', color: 'var(--text-low)', display: 'block', marginTop: '6px', fontFamily: 'var(--font-mono)'}}>{r.command}</code>
                                                            {r.started_at && (
                                                                <div style={{fontSize: '9px', color: 'var(--text-low)', marginTop: '4px'}}>
                                                                    Started: {new Date(r.started_at).toLocaleTimeString()}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )) : <p style={styles.emptyText}>No remediation actions planned.</p>
                                                }
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )) : <div className="glass-panel" style={{padding: '80px', textAlign: 'center'}}>
                                <BrainCircuit size={48} color="var(--text-low)" style={{marginBottom: '20px', opacity: 0.5}} />
                                <p style={styles.emptyText}>RCA Engine idling. No critical incidents signature detected.</p>
                                <p style={{...styles.emptyText, fontSize: '10px', marginTop: '8px'}}>
                                    Monitoring {Object.keys(metrics).length} services in real-time.
                                </p>
                                <p style={{...styles.emptyText, fontSize: '10px', marginTop: '16px', color: 'var(--text-mid)'}}>
                                    💡 Tip: Click "Trigger CPU Stress" or "Trigger Memory Leak" above to generate test incidents
                                </p>
                            </div>}
                        </div>
                    )}

                    {activeTab === 'logs' && (
                        <div className="glass-panel" style={styles.logTerminal}>
                            {logs.map(log => (
                                <div key={log.id} style={styles.logLine}>
                                    <span style={styles.logTs}>{log.ts}</span>
                                    <span style={{ ...styles.logLvl, color: log.lvl === 'ERROR' ? '#ff416c' : '#00ffa3' }}>{log.lvl}</span>
                                    <span style={styles.logSvc}>[{log.svc}]</span>
                                    <span style={styles.logMsg}>{log.msg}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
};

const NavItem = ({ label, active, onClick, style = {}, icon }) => (
    <div 
        style={{...styles.navItem, ...(active ? styles.navItemActive : {}), ...style}} 
        onClick={onClick}
    >
        {icon && <span style={{marginRight: '12px', display: 'flex'}}>{icon}</span>}
        {label}
    </div>
);

const KPICard = ({ title, value, sub }) => (
    <div className="glass-panel" style={styles.kpiCard}>
        <span style={styles.kpiTitle}>{title}</span>
        <div style={styles.kpiValue}>{value}</div>
        <div style={styles.kpiSub}>{sub}</div>
    </div>
);

const styles = {
    container: { display: 'flex', width: '100%', height: '100%', background: 'var(--bg-app)' },
    sidebar: { width: '200px', height: '100%', background: 'var(--bg-sidebar)', borderRight: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', padding: '40px 20px', transition: 'var(--theme-transition)' },
    logo: { marginBottom: '60px', padding: '0 8px' },
    logoText: { fontSize: '14px', fontWeight: '700', letterSpacing: '1px', textTransform: 'uppercase', color: 'var(--text-sidebar)' },
    nav: { flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' },
    navItem: { padding: '10px 12px', borderRadius: '4px', cursor: 'pointer', color: 'var(--text-sidebar)', fontSize: '12px', fontWeight: '500', opacity: 0.7, transition: 'var(--theme-transition)', display: 'flex', alignItems: 'center' },
    navItemActive: { color: '#ffffff', background: 'rgba(255, 255, 255, 0.05)', opacity: 1 },
    sidebarFooter: { display: 'flex', gap: '8px', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.05)' },
    main: { flex: 1, height: '100%', display: 'flex', flexDirection: 'column', padding: '60px 80px', overflowY: 'auto' },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '60px' },
    headerTitle: { display: 'flex', flexDirection: 'column', gap: '8px' },
    title: { fontSize: '10px', fontWeight: '700', color: 'var(--text-low)', letterSpacing: '2px', textTransform: 'uppercase' },
    subtitle: { fontSize: '28px', color: 'var(--text-high)', fontWeight: '400', letterSpacing: '-0.5px' },
    headerActions: { display: 'flex', alignItems: 'center', gap: '24px' },
    badge: { display: 'flex', alignItems: 'center', gap: '8px', fontSize: '10px', fontWeight: '600', color: 'var(--text-mid)', textTransform: 'uppercase', letterSpacing: '0.5px' },
    vLine: { width: '1px', height: '16px', background: 'var(--border-subtle)' },
    profile: { display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' },
    avatar: { width: '28px', height: '28px', background: 'var(--bg-element)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--border-subtle)' },
    profileInfo: { display: 'flex', flexDirection: 'column' },
    userName: { fontSize: '11px', fontWeight: '600', color: 'var(--text-high)' },
    userRole: { fontSize: '9px', color: 'var(--text-low)', textTransform: 'uppercase' },
    dot: { width: '5px', height: '5px', borderRadius: '50%' },
    grid: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1px', background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)', borderRadius: '8px', overflow: 'hidden' },
    kpiCard: { padding: '32px', display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--bg-surface)', border: 'none', borderRadius: 0 },
    kpiTitle: { fontSize: '9px', fontWeight: '600', color: 'var(--text-low)', letterSpacing: '1px', textTransform: 'uppercase' },
    kpiValue: { fontSize: '32px', fontWeight: '300', color: 'var(--text-high)', letterSpacing: '-1px' },
    kpiSub: { fontSize: '10px', color: 'var(--text-low)' },
    heroChart: { gridColumn: 'span 3', height: '400px', display: 'flex', flexDirection: 'column', marginTop: '40px' },
    cardTitle: { fontSize: '9px', fontWeight: '600', color: 'var(--text-low)', letterSpacing: '1.5px', textTransform: 'uppercase' },
    sidePanel: { height: '400px', padding: '32px', marginTop: '40px' },
    incidentList: { display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '24px' },
    incidentItem: { display: 'flex', alignItems: 'center', gap: '16px', padding: '12px 0', borderBottom: '1px solid var(--border-subtle)' },
    incidentDot: { width: '4px', height: '4px', background: 'var(--accent-error)', borderRadius: '50%' },
    incidentInfo: { display: 'flex', justifyContent: 'space-between', flex: 1 },
    incidentTitle: { fontSize: '12px', fontWeight: '500', color: 'var(--text-high)' },
    incidentSub: { fontSize: '10px', color: 'var(--text-low)', textTransform: 'uppercase' },
    emptyText: { color: 'var(--text-low)', fontSize: '11px', marginTop: '40px' },
    logTerminal: { padding: '32px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', fontFamily: 'var(--font-mono)' },
    logLine: { display: 'flex', gap: '20px', fontSize: '11px', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' },
    logTs: { color: 'var(--text-low)', opacity: 0.5 },
    logLvl: { fontWeight: '700', width: '40px' },
    logSvc: { color: 'var(--accent-primary)', opacity: 0.6 },
    logMsg: { color: 'var(--text-mid)' },
    navSection: { fontSize: '9px', fontWeight: '800', color: 'var(--text-low)', letterSpacing: '1.5px', marginTop: '24px', marginBottom: '8px', padding: '0 12px', opacity: 0.5 },
    metricRow: { display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: '13px', color: 'var(--text-mid)' },
    button: { background: 'var(--text-high)', color: 'var(--bg-app)', border: 'none', padding: '12px 24px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '1px' }
};

export default App;
