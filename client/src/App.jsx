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

const App = () => {
    const { connected, metrics, anomalies, incidents, remediations, logs, triggerSimulation } = useSmartOps();
    const [activeTab, setActiveTab] = useState('overview');
    const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
    const [user, setUser] = useState(JSON.parse(localStorage.getItem('user')));

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

    if (!user) return <Login onLogin={handleLogin} theme={theme} />;

    const chartData = {
        labels: Array(20).fill(''),
        datasets: [{
            label: 'Global Throughput',
            data: Array(20).fill(0).map(() => Math.floor(Math.random() * 50)),
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
                        <h1 style={styles.title}>{activeTab}</h1>
                        <p style={styles.subtitle}>Autonomous Control</p>
                    </div>
                    <div style={styles.headerActions}>
                        <div style={styles.badge}>
                            <div style={{...styles.dot, background: connected ? 'var(--accent-success)' : 'var(--accent-error)'}}></div>
                            {connected ? 'Sync Active' : 'Offline'}
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
                            <KPICard title="HEALTH" value="99.9%" sub="High availability" />
                            <KPICard title="EVENTS" value={anomalies.length} sub="Real-time scan" />
                            <KPICard title="LOAD" value="1.2k" sub="Req / Sec" />
                            <KPICard title="RESOLVED" value={remediations.length} sub="Autonomous" />

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
                        <div className="glass-panel" style={{padding: '40px', textAlign: 'center'}}>
                            <K6Icon size={48} color="var(--accent-primary)" style={{marginBottom: '20px'}} />
                            <h2 style={styles.subtitle}>Load Generation Engine</h2>
                            <p style={{...styles.logMsg, marginTop: '20px'}}>Active Scenarios: 0</p>
                            <button 
                                style={{...styles.button, width: '200px', alignSelf: 'center', marginTop: '40px'}}
                                onClick={() => triggerSimulation('cpu_stress', 'order_service')}
                            >
                                Start Stress Test
                            </button>
                        </div>
                    )}

                    {activeTab === 'k8s' && (
                        <div className="glass-panel" style={{padding: '40px'}}>
                            <h3 style={styles.cardTitle}>Cluster Topology</h3>
                            <div style={{...styles.logTerminal, marginTop: '24px'}}>
                                <div style={styles.logLine}>[K8S] NODE: master-01 STATUS: Ready ROLE: Control Plane</div>
                                <div style={styles.logLine}>[K8S] NODE: worker-01 STATUS: Ready ROLE: Worker</div>
                                <div style={styles.logLine}>[K8S] NODE: worker-02 STATUS: Ready ROLE: Worker</div>
                                <div style={{...styles.logLine, marginTop: '20px', border: 'none'}}>Current Context: smartops-prod-cluster</div>
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
                            {incidents.length > 0 ? incidents.map(ici => (
                                <div key={ici.incident_id} className="glass-panel" style={{padding: '40px'}}>
                                    <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: '24px'}}>
                                        <h2 style={styles.subtitle}>{ici.primary_cause}</h2>
                                        <span style={{...styles.badge, color: 'var(--accent-error)'}}>ID: {ici.incident_id}</span>
                                    </div>
                                    <p style={{...styles.logMsg, marginBottom: '32px', fontSize: '14px'}}>{ici.ai_summary}</p>
                                    
                                    <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '40px'}}>
                                        <div>
                                            <h3 style={styles.cardTitle}>Contributing Factors</h3>
                                            <div style={{marginTop: '16px'}}>
                                                {ici.causes.map((c, i) => (
                                                    <div key={i} style={{padding: '12px 0', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between'}}>
                                                        <span style={styles.logMsg}>{c.cause}</span>
                                                        <span style={{color: 'var(--accent-primary)', fontSize: '12px'}}>{(c.probability * 100).toFixed(0)}%</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                        <div>
                                            <h3 style={styles.cardTitle}>Remediation Protocol</h3>
                                            <div style={{marginTop: '16px'}}>
                                                {remediations.filter(r => r.incident_id === ici.incident_id).map(r => (
                                                    <div key={r.id} style={{padding: '12px 0', borderBottom: '1px solid var(--border-subtle)'}}>
                                                        <div style={{display: 'flex', justifyContent: 'space-between'}}>
                                                            <span style={{fontSize: '12px', color: 'var(--text-high)'}}>{r.title}</span>
                                                            <span style={{fontSize: '10px', color: 'var(--accent-success)', textTransform: 'uppercase'}}>{r.status}</span>
                                                        </div>
                                                        <code style={{fontSize: '10px', color: 'var(--text-low)', display: 'block', marginTop: '6px'}}>{r.command}</code>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )) : <div className="glass-panel" style={{padding: '80px', textAlign: 'center'}}>
                                <p style={styles.emptyText}>RCA Engine idling. No critical incidents signature detected.</p>
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
