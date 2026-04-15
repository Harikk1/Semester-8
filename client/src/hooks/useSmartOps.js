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
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'init' || data.type === 'metrics_update') {
                    setState(s => ({
                        ...s,
                        metrics: data.metrics || s.metrics,
                        anomalies: data.anomalies ? [...data.anomalies, ...s.anomalies].slice(0, 50) : s.anomalies,
                        incidents: data.rcas ? [...data.rcas, ...s.incidents].slice(0, 20) : s.incidents,
                        remediations: data.remediations ? [...data.remediations, ...s.remediations].slice(0, 20) : s.remediations,
                        autoRem: data.auto_rem ?? s.autoRem,
                        lastUpdate: data.timestamp
                    }));

                    if (data.rcas?.length) {
                        data.rcas.forEach(r => addLog('AI-RCA', 'INFO', `Incident Analyzed: ${r.incident_id}`));
                    }
                }
            };

            socket.onclose = () => {
                setState(s => ({ ...s, connected: false }));
                addLog('HUB', 'ERROR', 'Disconnected from Engine. Retrying...');
                setTimeout(connect, 5000);
            };

            ws.current = socket;
        };

        connect();
        return () => ws.current?.close();
    }, [addLog]);

    const triggerSimulation = async (scenario, service) => {
        try {
            const res = await fetch(`http://localhost:9000/api/simulate/${scenario}/${service}`, { method: 'POST' });
            if (res.ok) addLog('OPERATOR', 'WARN', `Simulation triggered: ${scenario} on ${service}`);
        } catch (e) {
            addLog('HUB', 'ERROR', `Simulation failed: ${e.message}`);
        }
    };

    return { ...state, logs, triggerSimulation };
}
