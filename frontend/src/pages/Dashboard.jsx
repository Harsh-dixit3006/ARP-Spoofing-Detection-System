import React, { useEffect, useState, useRef } from 'react';
import socket from '../services/socket';
import api from '../services/api';
import { useNavigate } from 'react-router-dom';
import { 
  Shield, 
  ShieldAlert, 
  Activity, 
  AlertTriangle, 
  Clock, 
  Server,
  Radio,
  Wifi,
  Loader2,
  CheckCircle2,
  LogOut
} from 'lucide-react';
import { ToastContainer, toast } from 'react-toastify';

const Dashboard = () => {
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({ total_alerts: 0, active_attackers: [] });
  const [loading, setLoading] = useState(true);
  const [initialLoad, setInitialLoad] = useState(true);
  const navigate = useNavigate();

  const playAlertSound = () => {
    try {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const audioCtx = audioRef.current || (AudioContextClass && new AudioContextClass());
  if (!audioCtx) return;

  // If we created a new AudioContext here (fallback), keep it in ref so subsequent plays are allowed
  if (!audioRef.current) audioRef.current = audioCtx;

  const oscillator = audioCtx.createOscillator();
  const gainNode = audioCtx.createGain();

  oscillator.type = 'square';
  oscillator.frequency.setValueAtTime(800, audioCtx.currentTime);
  oscillator.frequency.exponentialRampToValueAtTime(400, audioCtx.currentTime + 0.5);

  gainNode.gain.setValueAtTime(0.5, audioCtx.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);

  oscillator.connect(gainNode);
  gainNode.connect(audioCtx.destination);

  oscillator.start();
  oscillator.stop(audioCtx.currentTime + 0.5);
    } catch (e) {
      console.log('Audio playback prevented by browser policy');
    }
  };

  // Central AudioContext ref unlocked by user interaction to satisfy browser autoplay policies
  const audioRef = useRef(null);
  const [alertsEnabled, setAlertsEnabled] = useState(!!localStorage.getItem('alerts_enabled'));

  const enableAlerts = async () => {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;
      // create and resume audio context on user gesture
      const ctx = new AudioContextClass();
      // create tiny buffer to unlock audio on Safari/Chrome
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.connect(g);
      g.connect(ctx.destination);
      osc.start();
      // stop immediately to unlock
      g.gain.setValueAtTime(0, ctx.currentTime + 0.01);
      osc.stop(ctx.currentTime + 0.02);
      // keep the context for future plays
      audioRef.current = ctx;
      await ctx.resume();
      setAlertsEnabled(true);
      localStorage.setItem('alerts_enabled', '1');
    } catch (e) {
      console.log('Failed to enable alerts:', e);
    }
  };

  const disableAlerts = async () => {
    try {
      if (audioRef.current) {
        await audioRef.current.close();
        audioRef.current = null;
      }
    } catch (e) {
      console.log('Error closing audio context', e);
    }
    setAlertsEnabled(false);
    localStorage.removeItem('alerts_enabled');
  };

  const playSiren = (duration = 3000) => {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      const audioCtx = audioRef.current || (AudioContextClass && new AudioContextClass());
      if (!audioCtx) return;
      if (!audioRef.current) audioRef.current = audioCtx;

      const oscillator = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      oscillator.type = 'sawtooth';
      oscillator.frequency.setValueAtTime(1200, audioCtx.currentTime);
      gainNode.gain.setValueAtTime(0.6, audioCtx.currentTime);
      oscillator.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      oscillator.start();
      setTimeout(() => {
        try {
          gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.5);
          oscillator.stop(audioCtx.currentTime + 0.6);
        } catch (e) {
          // ignore if audio context closed
        }
      }, duration);
    } catch (e) {
      console.log('Siren playback prevented by browser policy');
    }
  };

  

  

  const resetDashboard = async () => {
    try {
      await api.delete('/alerts/clear-alerts');
      toast.success('Dashboard Resetted', { theme: 'dark' });
      setAlerts([]);
      setStats({ total_alerts: 0, active_attackers: [] });
    } catch (e) {
      toast.error('Reset Failed', { theme: 'dark' });
    }
  };

  const simulateAttack = async () => {
    try {
      await api.post('/alerts/test-attack');
      toast.info('Simulated attack triggered', { theme: 'dark' });
    } catch (e) {
      toast.error('Simulator error', { theme: 'dark' });
    }
  };

  const handleLogout = () => {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      navigate('/login');
  };

  // Fetch initial alerts and stats
  useEffect(() => {
    let mounted = true;
    const fetchAlerts = async () => {
      try {
        const res = await api.get('/alerts');
        if (!mounted) return;
        if (res.data && res.data.alerts) {
          setAlerts(res.data.alerts);
          setStats({ total_alerts: res.data.total_alerts || res.data.alerts.length, active_attackers: res.data.active_attackers || [] });
        }
      } catch (e) {
        console.log('Failed to fetch alerts', e);
      } finally {
        setLoading(false);
        setInitialLoad(false);
      }
    };
    fetchAlerts();
    return () => { mounted = false; };
  }, []);

  // Real‑time socket listener
  useEffect(() => {
    const handleNewAlert = (alert) => {
      // Prepend to alerts list
      setAlerts(prev => [alert, ...prev]);
      // Update stats quickly
      setStats(prev => ({
        total_alerts: prev.total_alerts + 1,
        active_attackers: prev.active_attackers.includes(alert.ip) ? prev.active_attackers : [...prev.active_attackers, alert.ip]
      }));
      playAlertSound();
      toast.error('New ARP Spoofing Alert Detected!', { theme: 'dark', position: 'top-right' });
    };
    socket.on('new_alert', handleNewAlert);
    const handleSiren = (data) => {
      playSiren(4000);
    };
    socket.on('siren', handleSiren);
    return () => {
      socket.off('new_alert', handleNewAlert);
      socket.off('siren', handleSiren);
    };
  }, []);


  const totalAlerts = stats.total_alerts;
  const highSeverityCount = alerts.filter(a => a.severity === 'HIGH').length;
  const lastAttackTime = alerts.length > 0 ? alerts[0].time : 'Never';
  const isUnderAttack = stats.active_attackers.length > 0 || (alerts.length > 0 && (Date.now() / 1000 - alerts[0].timestamp < 60));

  const getSeverityStyle = (severity) => {
    switch(severity) {
      case 'HIGH': return { bg: 'bg-red-500/10', text: 'text-red-500', border: 'border-red-500/50', glow: 'shadow-[0_0_15px_rgba(239,68,68,0.5)]' };
      case 'MEDIUM': return { bg: 'bg-orange-500/10', text: 'text-orange-500', border: 'border-orange-500/50', glow: 'shadow-[0_0_15px_rgba(249,115,22,0.5)]' };
      case 'LOW': return { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/50', glow: 'shadow-[0_0_15px_rgba(234,179,8,0.5)]' };
      default: return { bg: 'bg-slate-500/10', text: 'text-slate-400', border: 'border-slate-500/50', glow: '' };
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 p-4 md:p-8 font-sans selection:bg-blue-500/30">
      <ToastContainer />
      
      {/* Grid Background overlay for tech feel */}
      <div className="fixed inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none"></div>
      <div className="fixed inset-0 bg-[radial-gradient(circle_800px_at_50%_-30%,#1e3a8a33,transparent)] pointer-events-none"></div>

      <div className="max-w-7xl mx-auto relative z-10 space-y-8">
        
        {/* Header section */}
        <header className="flex flex-col md:flex-row items-center justify-between border-b border-slate-800 pb-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500 blur-xl opacity-20 hover:opacity-40 transition-opacity"></div>
              <div className="p-3 bg-slate-900 border border-blue-500/30 rounded-xl relative">
                <Radio className="w-8 h-8 text-blue-400" />
              </div>
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent uppercase tracking-wider">
                Real-Time ARP Spoofing Monitor
              </h1>
              <div className="flex items-center gap-2 mt-1">
                <Wifi className="w-4 h-4 text-emerald-400 animate-pulse" />
                <span className="text-slate-400 text-sm tracking-widest uppercase">Live SOC Terminal • {new Date().toLocaleTimeString()}</span>
              </div>
            </div>
          </div>
          
          <div className="mt-6 md:mt-0 flex flex-wrap items-center gap-3 md:gap-4">
             {/* Simulator Controls */}
             <button onClick={simulateAttack} className="px-4 py-2.5 bg-red-600 hover:bg-red-500 text-white font-bold rounded-xl shadow-[0_0_15px_rgba(239,68,68,0.4)] hover:shadow-[0_0_25px_rgba(239,68,68,0.6)] transition-all flex items-center gap-2 text-xs md:text-sm uppercase tracking-wider cursor-pointer active:scale-95">
               <AlertTriangle className="w-4 h-4" /> Simulate Attack
             </button>
             {!alertsEnabled ? (
               <button onClick={enableAlerts} className="px-4 py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-bold rounded-xl border border-amber-700 transition-all flex items-center gap-2 text-xs md:text-sm uppercase tracking-wider cursor-pointer active:scale-95">
                 Enable Alerts
               </button>
             ) : (
               <button onClick={disableAlerts} className="px-4 py-2.5 bg-emerald-700 hover:bg-emerald-600 text-white font-bold rounded-xl border border-emerald-800 transition-all flex items-center gap-2 text-xs md:text-sm uppercase tracking-wider cursor-pointer active:scale-95">
                 Alerts Enabled
               </button>
             )}
             <button onClick={resetDashboard} className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl border border-slate-600 hover:border-slate-500 transition-all flex items-center gap-2 text-xs md:text-sm uppercase tracking-wider cursor-pointer active:scale-95">
               <Shield className="w-4 h-4" /> Reset
             </button>
             <button onClick={handleLogout} className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl border border-slate-600 hover:border-slate-500 transition-all flex items-center gap-2 text-xs md:text-sm uppercase tracking-wider cursor-pointer active:scale-95">
               <LogOut className="w-4 h-4" /> Disconnect
             </button>

             {/* System Polling Status */}
             <div className="ml-2 px-4 py-2 bg-slate-900 border border-slate-700 rounded-xl flex items-center gap-3">
               <div className="flex flex-col text-right">
                 <span className="text-[10px] text-slate-500 uppercase tracking-widest leading-tight">System Status</span>
                 <span className="text-xs font-bold text-slate-300">Polling (3s)</span>
               </div>
               {loading ? <Loader2 className="w-4 h-4 text-blue-400 animate-spin" /> : <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]"></div>}
             </div>
          </div>

        </header>

        {/* Dynamic Status Card */}
        <div className={`relative overflow-hidden rounded-2xl border backdrop-blur-sm transition-all duration-700 ${
          isUnderAttack 
            ? 'bg-red-950/40 border-red-500/50 shadow-[0_0_40px_rgba(239,68,68,0.2)]' 
            : 'bg-emerald-950/20 border-emerald-500/30 shadow-[0_0_40px_rgba(16,185,129,0.1)]'
        }`}>
          <div className="p-8 md:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              <div className="relative">
                {isUnderAttack ? (
                  <>
                    <div className="absolute inset-0 bg-red-500 blur-2xl opacity-40 animate-pulse"></div>
                    <div className="p-5 bg-red-500/10 rounded-2xl border border-red-500/50 relative z-10">
                      <AlertTriangle className="w-14 h-14 text-red-500" />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="absolute inset-0 bg-emerald-500 blur-xl opacity-20"></div>
                    <div className="p-5 bg-emerald-500/10 rounded-2xl border border-emerald-500/30 relative z-10">
                      <Shield className="w-14 h-14 text-emerald-400" />
                    </div>
                  </>
                )}
              </div>
              
              <div>
                <h2 className={`text-4xl md:text-5xl font-black uppercase tracking-tight ${isUnderAttack ? 'text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)]' : 'text-emerald-400 drop-shadow-[0_0_15px_rgba(16,185,129,0.5)]'}`}>
                  {isUnderAttack ? 'UNDER ATTACK' : 'NETWORK SECURE'}
                </h2>
                <p className="text-slate-300 text-lg md:text-xl mt-2 max-w-2xl">
                  {isUnderAttack 
                    ? 'CRITICAL EXPLOIT DETECTED: Active ARP Cache Poisoning originating from local subnet. Immediate mitigation required.' 
                    : 'All monitored subnets are currently clear of malicious ARP broadcasting. No spoofing signatures detected.'}
                </p>
              </div>
            </div>

            {isUnderAttack && (
              <div className="flex items-center justify-center">
                <div className="w-32 h-32 rounded-full border-4 border-red-500/30 border-t-red-500 animate-spin flex items-center justify-center relative">
                  <div className="absolute inset-0 rounded-full border-4 border-red-500/10 border-b-red-500 animate-[spin_3s_linear_reverse]"></div>
                  <span className="text-red-500 font-bold animate-pulse absolute">DEFEND</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-700/50 rounded-xl p-6 hover:bg-slate-800/50 transition-colors relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl group-hover:bg-blue-500/20 transition-colors"></div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm font-semibold uppercase tracking-widest mb-1">Total Alerts</p>
                <h3 className="text-5xl font-black text-white">{totalAlerts}</h3>
              </div>
              <div className="p-4 bg-slate-800 text-blue-400 rounded-xl border border-slate-700">
                <Activity className="w-8 h-8" />
              </div>
            </div>
            <div className="mt-4 text-sm text-slate-500 font-medium tracking-wide">Lifetime threat signatures logged</div>
          </div>

          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-700/50 rounded-xl p-6 hover:bg-slate-800/50 transition-colors relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/10 rounded-full blur-3xl group-hover:bg-red-500/20 transition-colors"></div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm font-semibold uppercase tracking-widest mb-1">High Severity</p>
                <h3 className="text-5xl font-black text-red-500 drop-shadow-[0_0_10px_rgba(239,68,68,0.3)]">{highSeverityCount}</h3>
              </div>
              <div className="p-4 bg-red-500/10 text-red-500 rounded-xl border border-red-500/20">
                <ShieldAlert className="w-8 h-8" />
              </div>
            </div>
            <div className="mt-4 text-sm text-slate-500 font-medium tracking-wide">Repeated persistent attack attempts</div>
          </div>

          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-700/50 rounded-xl p-6 hover:bg-slate-800/50 transition-colors relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-3xl group-hover:bg-indigo-500/20 transition-colors"></div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm font-semibold uppercase tracking-widest mb-1">Last Attack</p>
                <h3 className="text-xl font-bold text-white mt-2 max-w-[150px] truncate">{lastAttackTime}</h3>
              </div>
              <div className="p-4 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
                <Clock className="w-8 h-8" />
              </div>
            </div>
            <div className="mt-4 text-sm text-slate-500 font-medium tracking-wide">Most recent violation logged</div>
          </div>
        </div>

        {/* Live Alerts Section */}
        {alerts.length > 0 && (
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-xl font-bold flex items-center gap-2 text-slate-200">
              <Activity className="w-5 h-5 text-blue-400" /> Recent Live Threats
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {alerts.slice(0, 3).map((alert, idx) => {
                const style = getSeverityStyle(alert.severity);
                return (
                  <div key={`live-${idx}`} className={`p-5 rounded-xl border ${style.bg} ${style.border} ${style.glow} backdrop-blur-sm relative overflow-hidden hover:scale-[1.02] transition-transform cursor-default`}>
                     <div className="flex justify-between items-start mb-3">
                       <span className={`px-2 py-1 text-xs font-bold rounded uppercase tracking-wider bg-black/40 ${style.text} border ${style.border}`}>
                         {alert.severity} SEVERITY
                       </span>
                       <span className="text-xs text-slate-400 font-mono">{alert.time.split(' ')[3]}</span>
                     </div>
                     <p className="font-mono text-sm text-slate-300 mb-1">Attacker IP: <span className="text-white font-bold">{alert.ip}</span></p>
                     <p className="font-mono text-xs text-slate-400 mb-1">Fake MAC: <span className="text-yellow-400">{alert.fake_mac}</span></p>
                     <p className="font-mono text-xs text-slate-400">Real MAC: <span className="text-emerald-400">{alert.real_mac || 'Unknown'}</span></p>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Detailed Attack Logs Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative">
          <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-900/80 backdrop-blur-md">
            <h2 className="text-xl font-bold flex items-center gap-3 text-slate-200">
              <Server className="w-5 h-5 text-blue-400" /> Historical Attack Logs
            </h2>
            <span className="text-xs font-semibold text-slate-500 bg-slate-800 px-3 py-1 rounded-full border border-slate-700 tracking-wide uppercase">Displaying Last 100 Entries</span>
          </div>
          
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto bg-slate-950">
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-24 px-4 text-center animate-in zoom-in duration-500">
                <div className="w-24 h-24 bg-emerald-500/10 rounded-full flex items-center justify-center mb-6 border border-emerald-500/20 shadow-[0_0_40px_rgba(16,185,129,0.2)]">
                  <CheckCircle2 className="w-12 h-12 text-emerald-400" />
                </div>
                <h3 className="text-3xl font-bold text-emerald-400 mb-3 tracking-tight">No threats detected</h3>
                <p className="text-slate-400 text-lg max-w-lg leading-relaxed">Your network is currently secure. The monitoring system is actively scanning for ARP anomalies.</p>
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 z-10 bg-slate-900 border-b border-slate-800 shadow-md">
                  <tr className="text-slate-400 text-xs uppercase tracking-widest font-semibold">
                    <th className="py-4 px-6 border-b border-slate-800 w-1/4">Timestamp</th>
                    <th className="py-4 px-6 border-b border-slate-800">Attacker IP</th>
                    <th className="py-4 px-6 border-b border-slate-800">Spoofed MAC</th>
                    <th className="py-4 px-6 border-b border-slate-800">Legitimate MAC</th>
                    <th className="py-4 px-6 border-b border-slate-800 text-center">Threat Level</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-sm">
                  {alerts.map((alert, index) => {
                    const style = getSeverityStyle(alert.severity);
                    return (
                      <tr 
                        key={alert.alert_id || alert.timestamp + index} 
                        className="hover:bg-slate-800/60 even:bg-slate-900/40 transition-colors group cursor-default"
                      >
                        <td className="py-4 px-6 font-mono text-slate-400 group-hover:text-slate-300 transition-colors">{alert.time}</td>
                        <td className="py-4 px-6 font-mono font-bold text-red-400">{alert.ip}</td>
                        <td className="py-4 px-6 font-mono text-yellow-500">{alert.fake_mac}</td>
                        <td className="py-4 px-6 font-mono text-emerald-400">{alert.real_mac || 'Unknown'}</td>
                        <td className="py-4 px-6 text-center">
                          <span className={`inline-block px-3 py-1 text-xs font-bold rounded border ${style.bg} ${style.text} ${style.border}`}>
                            {alert.severity}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
        
      </div>
    </div>
  );
};

export default Dashboard;
