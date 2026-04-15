import { useState, useEffect, useRef, useCallback } from 'react';

const ENGINE_WS = 'ws://localhost:9000/ws';

export function useSmartOps() {
    const [state, setState] = useState({
        connected: false,
        metrics: {},
        anomalies: [],
        incidents: [],
        remediations: [],
        autoRem: true,
        lastUpdate: null
    });

    const [logs, setLogs] = useState([]);
    const ws = useRef(null);
    const reconnectTimeout = useRef(null);

    const addLog = useCallback((svc, lvl, msg) => {
        setLogs(prev => [{
            ts: new Date().toLocaleTimeString(),
            svc,
            lvl,
            msg,
            id: Date.now() + Math.random()
        }, ...prev].slice(0, 100));
    }, []);

    useEffect(() => {
        const connect = () => {
            console.log('Connecting to SmartOps Engine...');
            const socket = new WebSocket(ENGINE_WS);

            socket.onopen = () => {
                setState(s => ({ ...s, connected: true }));
                addLog('HUB', 'SUCCESS', 'Connected to SmartOps AI Engine.');
                if (reconnectTimeout.current) {
                    clearTimeout(reconnectTimeout.current);
                    reconnectTimeout.current = null;
                }
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'init' || data.type === 'metrics_update') {
                    setState(s => {
                        // Merge new data with existing, keeping unique incidents
                        const existingIncidentIds = new Set(s.incidents.map(i => i.incident_id));
                        const newIncidents = data.rcas ? data.rcas.filter(r => !existingIncidentIds.has(r.incident_id)) : [];
                        
                        const existingAnomalyIds = new Set(s.anomalies.map(a => a.id));
                        const newAnomalies = data.anomalies ? data.anomalies.filter(a => !existingAnomalyIds.has(a.id)) : [];
                        
                        const existingRemediationIds = new Set(s.remediations.map(r => r.id));
                        const newRemediations = data.remediations ? data.remediations.filter(r => !existingRemediationIds.has(r.id)) : [];
                        
                        return {
                            ...s,
                            metrics: data.metrics || s.metrics,
                            anomalies: [...newAnomalies, ...s.anomalies].slice(0, 100),
                            incidents: [...newIncidents, ...s.incidents].slice(0, 50),
                            remediations: [...newRemediations, ...s.remediations].slice(0, 100),
                            autoRem: data.auto_rem ?? s.autoRem,
                            lastUpdate: data.timestamp || new Date().toISOString()
                        };
                    });

                    if (data.rcas?.length) {
                        data.rcas.forEach(r => addLog('AI-RCA', 'INFO', `Incident Analyzed: ${r.incident_id} - ${r.primary_cause}`));
                    }
                    
                    if (data.anomalies?.length) {
                        data.anomalies.forEach(a => {
                            if (a.severity === 'critical') {
                                addLog('DETECTOR', 'ERROR', `Critical anomaly: ${a.service}.${a.metric} = ${a.value}`);
                            }
                        });
                    }
                }
            };

            socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                addLog('HUB', 'ERROR', 'Connection error occurred.');
            };

            socket.onclose = () => {
                setState(s => ({ ...s, connected: false }));
                addLog('HUB', 'ERROR', 'Disconnected from Engine. Retrying in 5s...');
                
                // Reconnect with exponential backoff
                reconnectTimeout.current = setTimeout(connect, 5000);
            };

            ws.current = socket;
        };

        connect();
        
        return () => {
            if (reconnectTimeout.current) {
                clearTimeout(reconnectTimeout.current);
            }
            if (ws.current) {
                ws.current.close();
            }
        };
    }, [addLog]);

    const triggerSimulation = async (scenario, service) => {
        try {
            const res = await fetch(`http://localhost:9000/api/simulate/${scenario}/${service}`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                addLog('OPERATOR', 'WARN', `Simulation triggered: ${scenario} on ${service}`);
                if (data.incident_id) {
                    addLog('AI-RCA', 'INFO', `Incident generated: ${data.incident_id}`);
                }
            } else {
                addLog('HUB', 'ERROR', `Simulation failed: ${res.statusText}`);
            }
        } catch (e) {
            addLog('HUB', 'ERROR', `Simulation failed: ${e.message}`);
        }
    };

    const generateDemoIncident = async () => {
        try {
            const res = await fetch('http://localhost:9000/api/demo/generate-incident', { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                addLog('DEMO', 'INFO', `Demo incident generated: ${data.incident?.incident_id}`);
            } else {
                addLog('HUB', 'ERROR', 'Failed to generate demo incident');
            }
        } catch (e) {
            addLog('HUB', 'ERROR', `Demo generation failed: ${e.message}`);
        }
    };

    return { ...state, logs, triggerSimulation, generateDemoIncident };
}
