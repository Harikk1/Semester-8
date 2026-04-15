import React, { useState } from 'react';

const Login = ({ onLogin, theme }) => {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        // Simulate auth
        onLogin({ email, name: email.split('@')[0] });
    };

    return (
        <div style={styles.page}>
            <div style={styles.card}>
                <header style={styles.header}>
                    <h1 style={styles.logo}>SmartOps AI</h1>
                    <p style={styles.subtitle}>
                        {isLogin ? 'Enter your credentials to access the node.' : 'Create a new operator account.'}
                    </p>
                </header>

                <form style={styles.form} onSubmit={handleSubmit}>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Operator ID</label>
                        <input 
                            type="email" 
                            style={styles.input} 
                            placeholder="email@enterprise.ai"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Access Key</label>
                        <input 
                            type="password" 
                            style={styles.input} 
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    <button type="submit" style={styles.button}>
                        {isLogin ? 'Initialize Session' : 'Create Account'}
                    </button>

                    <div style={styles.divider}>
                        <div style={styles.line}></div>
                        <span style={styles.dividerText}>or</span>
                        <div style={styles.line}></div>
                    </div>

                    <button type="button" style={styles.googleButton} onClick={() => handleSubmit({ preventDefault: () => {} })}>
                        <svg width="18" height="18" viewBox="0 0 24 24" style={styles.googleIcon}>
                            <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
                            <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                        Continue with Google
                    </button>
                </form>

                <footer style={styles.footer}>
                    <button style={styles.toggle} onClick={() => setIsLogin(!isLogin)}>
                        {isLogin ? "Don't have an account? Register" : "Already have an account? Login"}
                    </button>
                </footer>
            </div>
        </div>
    );
};

const styles = {
    page: { 
        width: '100vw', 
        height: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        background: 'var(--bg-app)',
        transition: 'var(--theme-transition)'
    },
    card: { 
        width: '380px', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '40px' 
    },
    header: { 
        textAlign: 'center', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '12px' 
    },
    logo: { 
        fontSize: '12px', 
        fontWeight: '700', 
        letterSpacing: '3px', 
        textTransform: 'uppercase', 
        color: 'var(--text-high)' 
    },
    subtitle: { 
        fontSize: '14px', 
        color: 'var(--text-low)', 
        lineHeight: '1.5' 
    },
    form: { 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '24px' 
    },
    inputGroup: { 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '8px' 
    },
    label: { 
        fontSize: '10px', 
        fontWeight: '600', 
        color: 'var(--text-low)', 
        textTransform: 'uppercase', 
        letterSpacing: '1px' 
    },
    input: { 
        background: 'var(--bg-surface)', 
        border: '1px solid var(--border-subtle)', 
        padding: '12px 16px', 
        borderRadius: '6px', 
        color: 'var(--text-high)', 
        fontSize: '14px', 
        outline: 'none',
        transition: 'var(--theme-transition)' 
    },
    button: { 
        background: 'var(--text-high)', 
        color: 'var(--bg-app)', 
        border: 'none', 
        padding: '14px', 
        borderRadius: '6px', 
        fontSize: '12px', 
        fontWeight: '700', 
        cursor: 'pointer', 
        textTransform: 'uppercase', 
        letterSpacing: '1px'
    },
    divider: {
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        margin: '8px 0'
    },
    line: {
        flex: 1,
        height: '1px',
        background: 'var(--border-subtle)'
    },
    dividerText: {
        fontSize: '10px',
        color: 'var(--text-low)',
        textTransform: 'uppercase'
    },
    googleButton: {
        background: 'transparent',
        border: '1px solid var(--border-subtle)',
        color: 'var(--text-high)',
        padding: '12px',
        borderRadius: '6px',
        fontSize: '12px',
        fontWeight: '600',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '12px',
        transition: 'var(--theme-transition)'
    },
    googleIcon: {
        color: 'var(--text-high)'
    },
    footer: { 
        textAlign: 'center' 
    },
    toggle: { 
        background: 'none', 
        border: 'none', 
        color: 'var(--text-low)', 
        fontSize: '11px', 
        cursor: 'pointer', 
        textDecoration: 'underline' 
    }
};

export default Login;
