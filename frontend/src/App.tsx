import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts';
import { 
  ShieldAlert, CheckCircle, Activity, Camera, Wifi, Server, 
  RotateCw, Filter, HardDrive, Cpu, AlertTriangle, Layers, Play
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:5000/api';
const IMAGE_BASE = `${API_BASE}/images`;

// Interfaces
interface Stats {
  total: number;
  monkey: number;
  clear: number;
  avg_conf: number;
}

interface LogEntry {
  test_number: string;
  timestamp: string;
  result: string;
  confidence_pct: string;
  saved_image: string;
}

// Sample Data for Demo Mode / Zero State visuals
const MOCK_STATS: Stats = {
  total: 48,
  monkey: 18,
  clear: 30,
  avg_conf: 87.5
};

const MOCK_LOGS: LogEntry[] = [
  { test_number: "48", timestamp: "2026-07-02 20:45:12", result: "monkey", confidence_pct: "92.4", saved_image: "demo1.jpg" },
  { test_number: "47", timestamp: "2026-07-02 19:30:00", result: "clear", confidence_pct: "0.0", saved_image: "demo2.jpg" },
  { test_number: "46", timestamp: "2026-07-02 18:15:34", result: "monkey", confidence_pct: "84.1", saved_image: "demo3.jpg" },
  { test_number: "45", timestamp: "2026-07-02 17:02:11", result: "clear", confidence_pct: "0.0", saved_image: "demo4.jpg" },
  { test_number: "44", timestamp: "2026-07-02 16:44:55", result: "clear", confidence_pct: "0.0", saved_image: "demo5.jpg" },
  { test_number: "43", timestamp: "2026-07-02 14:10:02", result: "monkey", confidence_pct: "89.8", saved_image: "demo6.jpg" },
  { test_number: "42", timestamp: "2026-07-02 13:05:18", result: "clear", confidence_pct: "0.0", saved_image: "demo7.jpg" },
  { test_number: "41", timestamp: "2026-07-02 11:22:40", result: "monkey", confidence_pct: "90.2", saved_image: "demo8.jpg" }
];

const MOCK_HOURLY = [
  { time: '08:00', monkey: 2, clear: 4, conf: 82 },
  { time: '10:00', monkey: 3, clear: 6, conf: 88 },
  { time: '12:00', monkey: 1, clear: 8, conf: 91 },
  { time: '14:00', monkey: 5, clear: 3, conf: 79 },
  { time: '16:00', monkey: 4, clear: 5, conf: 85 },
  { time: '18:00', monkey: 2, clear: 3, conf: 89 },
  { time: '20:00', monkey: 1, clear: 1, conf: 92 }
];

function App() {
  // Mode selection: "live" vs "demo"
  const [dataMode, setDataMode] = useState<'live' | 'demo'>('demo');
  
  // System status states
  const [serverStatus, setServerStatus] = useState<'online' | 'offline'>('offline');
  const [iotStatus, setIotStatus] = useState<'online' | 'offline'>('online');
  const [iotBattery, setIotBattery] = useState<number>(84);
  const [refreshing, setRefreshing] = useState(false);

  // Live state data
  const [liveStats, setLiveStats] = useState<Stats>({ total: 0, monkey: 0, clear: 0, avg_conf: 0 });
  const [liveLogs, setLiveLogs] = useState<LogEntry[]>([]);
  const [liveHourly, setLiveHourly] = useState<any[]>([]);

  // Filter state
  const [filterType, setFilterType] = useState<'all' | 'monkey' | 'clear'>('all');

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 6000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, logsRes] = await Promise.all([
        axios.get(`${API_BASE}/stats`),
        axios.get(`${API_BASE}/logs`)
      ]);
      setLiveStats(statsRes.data);
      setServerStatus('online');
      setLiveLogs(logsRes.data.reverse());
      processLiveHourly(logsRes.data);
    } catch (error) {
      setServerStatus('offline');
      console.error("API Connection Offline. Defaulting to Demo Mode visual experience.");
    }
  };

  const manualRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setTimeout(() => setRefreshing(false), 800);
  };

  const processLiveHourly = (data: LogEntry[]) => {
    const grouped: Record<string, any> = {};
    data.forEach(row => {
      const date = new Date(row.timestamp);
      if (isNaN(date.getTime())) return;
      const hourKey = `${date.getHours().toString().padStart(2, '0')}:00`;
      
      if (!grouped[hourKey]) grouped[hourKey] = { time: hourKey, monkey: 0, clear: 0, confSum: 0, confCount: 0 };
      if (row.result === 'monkey') {
        grouped[hourKey].monkey += 1;
        grouped[hourKey].confSum += parseFloat(row.confidence_pct);
        grouped[hourKey].confCount += 1;
      } else {
        grouped[hourKey].clear += 1;
      }
    });

    const formatted = Object.values(grouped).map(item => ({
      time: item.time,
      monkey: item.monkey,
      clear: item.clear,
      conf: item.confCount > 0 ? Math.round(item.confSum / item.confCount) : 0
    })).slice(-8);

    setLiveHourly(formatted);
  };

  // Determine active dataset based on mode
  const currentStats = dataMode === 'live' ? liveStats : MOCK_STATS;
  const currentLogs = dataMode === 'live' ? liveLogs : MOCK_LOGS;
  const currentHourly = dataMode === 'live' ? (liveHourly.length > 0 ? liveHourly : MOCK_HOURLY) : MOCK_HOURLY;

  // Filter logs
  const filteredLogs = currentLogs.filter(log => {
    if (filterType === 'all') return true;
    return log.result === filterType;
  });

  // KPI Calculations
  const totalScans = currentStats.total;
  const monkeyCount = currentStats.monkey;
  const clearCount = currentStats.clear;
  const averageConfidence = currentStats.avg_conf;

  // Pie chart datasets
  const pieData = [
    { name: 'Intrusions', value: monkeyCount, color: '#ef4444' },
    { name: 'Clear Checks', value: clearCount, color: '#10b981' }
  ];

  return (
    <div className="min-h-screen bg-[#070b13] text-[#cfd8e3] font-sans flex overflow-hidden">
      
      {/* 20-Year Exp BI Dev Sidebar: Power BI Style Filter Pane */}
      <aside className="w-80 bg-[#0d131f] border-r border-[#1e293b] flex-shrink-0 flex flex-col justify-between hidden lg:flex">
        <div className="p-6 space-y-6">
          <div className="flex items-center space-x-3 pb-4 border-b border-[#1e293b]">
            <Layers className="text-[#38bdf8] h-6 w-6 animate-pulse" />
            <div>
              <h2 className="text-md font-bold text-white tracking-widest uppercase text-xs">Analytics Portal</h2>
              <span className="text-[10px] text-slate-500 font-mono">ITT569 Farm Guard v4.1</span>
            </div>
          </div>

          {/* Report Controller Mode */}
          <div className="space-y-2">
            <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Report Environment</label>
            <div className="grid grid-cols-2 gap-1.5 p-1 bg-[#131b2e] rounded-lg border border-[#1e293b]">
              <button 
                onClick={() => setDataMode('live')}
                className={`py-1.5 px-3 text-xs font-semibold rounded-md transition ${dataMode === 'live' ? 'bg-[#38bdf8] text-[#070b13] shadow' : 'text-slate-400 hover:text-white'}`}
              >
                Live Production
              </button>
              <button 
                onClick={() => setDataMode('demo')}
                className={`py-1.5 px-3 text-xs font-semibold rounded-md transition ${dataMode === 'demo' ? 'bg-[#38bdf8] text-[#070b13] shadow' : 'text-slate-400 hover:text-white'}`}
              >
                Demo Sandbox
              </button>
            </div>
          </div>

          {/* BI Filter Pane */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <Filter size={14} /> Report Filters
            </h3>
            
            <div className="space-y-2">
              <button 
                onClick={() => setFilterType('all')}
                className={`w-full text-left py-2 px-3 rounded-lg text-xs font-medium border flex items-center justify-between transition ${filterType === 'all' ? 'bg-[#38bdf8]/10 text-white border-[#38bdf8]' : 'bg-[#131b2e]/50 text-slate-400 border-transparent hover:border-[#1e293b]'}`}
              >
                <span>All Detections</span>
                <span className="text-[10px] bg-[#1a233a] text-slate-300 px-2 py-0.5 rounded-full font-mono">{currentLogs.length}</span>
              </button>
              
              <button 
                onClick={() => setFilterType('monkey')}
                className={`w-full text-left py-2 px-3 rounded-lg text-xs font-medium border flex items-center justify-between transition ${filterType === 'monkey' ? 'bg-red-500/10 text-red-400 border-red-500' : 'bg-[#131b2e]/50 text-slate-400 border-transparent hover:border-[#1e293b]'}`}
              >
                <span className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-red-500"></div> Intrusions</span>
                <span className="text-[10px] bg-red-950/50 text-red-300 px-2 py-0.5 rounded-full font-mono">
                  {currentLogs.filter(l => l.result === 'monkey').length}
                </span>
              </button>

              <button 
                onClick={() => setFilterType('clear')}
                className={`w-full text-left py-2 px-3 rounded-lg text-xs font-medium border flex items-center justify-between transition ${filterType === 'clear' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500' : 'bg-[#131b2e]/50 text-slate-400 border-transparent hover:border-[#1e293b]'}`}
              >
                <span className="flex items-center gap-1.5"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div> Safe Frames</span>
                <span className="text-[10px] bg-emerald-950/50 text-emerald-300 px-2 py-0.5 rounded-full font-mono">
                  {currentLogs.filter(l => l.result === 'clear').length}
                </span>
              </button>
            </div>
          </div>

          {/* IoT Diagnostic Card */}
          <div className="bg-[#111827]/80 rounded-xl border border-[#1e293b] p-4 space-y-3 shadow-inner">
            <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">IoT Hardware Status</h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Node Battery:</span>
                <span className={`font-mono font-bold ${iotBattery > 20 ? 'text-emerald-400' : 'text-red-400'}`}>{iotBattery}%</span>
              </div>
              <div className="w-full bg-[#1e293b] h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full transition-all duration-500" style={{ width: `${iotBattery}%` }}></div>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">RSSI Power:</span>
                <span className="font-mono text-blue-400">-64 dBm</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">PIR Mode:</span>
                <span className="text-[#38bdf8] uppercase font-bold text-[10px]">Interference Trigger</span>
              </div>
            </div>
          </div>
        </div>

        {/* System Diagnostics */}
        <div className="p-6 border-t border-[#1e293b] space-y-4">
          <div className="flex items-center gap-3">
            <Cpu className="text-slate-500 h-5 w-5" />
            <div>
              <p className="text-[11px] text-slate-500 uppercase font-bold tracking-wider">Server CPU Load</p>
              <p className="text-sm font-semibold text-white font-mono">14.8%</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <HardDrive className="text-slate-500 h-5 w-5" />
            <div>
              <p className="text-[11px] text-slate-500 uppercase font-bold tracking-wider">Storage Capacity</p>
              <p className="text-sm font-semibold text-white font-mono">234.1 GB Free</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Body */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        
        {/* Top Header Bar */}
        <header className="bg-[#0b101b] border-b border-[#1e293b] py-4 px-6 md:px-8 flex items-center justify-between z-10 sticky top-0 backdrop-blur-md bg-opacity-90">
          <div className="flex items-center space-x-3">
            <span className="w-3 h-3 rounded-full bg-emerald-500 animate-ping"></span>
            <h1 className="text-lg font-bold text-white tracking-wide">
              PowerBI Live Dashboard
            </h1>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Quick Stats Indicator */}
            <div className="flex items-center gap-2 bg-[#131b2e]/60 px-3.5 py-1.5 rounded-lg border border-[#1e293b] text-xs font-mono">
              <span className="text-slate-500">Server Status:</span>
              <span className={serverStatus === 'online' ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                {serverStatus === 'online' ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>

            <button 
              onClick={manualRefresh}
              className={`p-2 bg-[#131b2e] hover:bg-[#1e293b] text-slate-300 hover:text-white rounded-lg border border-[#1e293b] transition duration-200 ${refreshing ? 'animate-spin' : ''}`}
            >
              <RotateCw size={15} />
            </button>
          </div>
        </header>

        {/* Dashboard Grid Panel */}
        <div className="p-6 md:p-8 space-y-6 flex-1">
          
          {/* Top Banner Alert (If Intrusion Detected Recently) */}
          {monkeyCount > 0 && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center justify-between text-red-400 animate-pulse">
              <div className="flex items-center space-x-3">
                <AlertTriangle size={20} className="text-red-500" />
                <span className="text-sm font-semibold">Alert: Active intruder detections in designated sector. Check live captures below.</span>
              </div>
              <span className="text-xs bg-red-950 text-red-300 font-bold px-2 py-0.5 rounded border border-red-800">CRITICAL</span>
            </div>
          )}

          {/* KPI Dashboard Ribbon */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
            <StatCard title="Total Detections" value={totalScans} label="All Sensor Captures" theme="blue" />
            <StatCard title="Intrusions" value={monkeyCount} label="Monkey Detected" theme="red" />
            <StatCard title="Safe Checks" value={clearCount} label="Clear Frames" theme="emerald" />
            <StatCard title="Avg. Inference Conf" value={`${averageConfidence}%`} label="YOLOv8 Accuracy" theme="purple" />
          </div>

          {/* Analytics Visualization Panel */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            
            {/* Timeline Visual - Area Graph */}
            <div className="xl:col-span-2 bg-[#0c1221] border border-[#1e293b]/70 rounded-xl p-6 shadow-2xl relative">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Detection Frequency Over Time</h3>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={currentHourly} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorIntrusion" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorClear" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                    <RechartsTooltip 
                      contentStyle={{ backgroundColor: '#0c1221', border: '1px solid #1e293b', borderRadius: '8px', color: '#f8fafc' }}
                    />
                    <Area type="monotone" dataKey="monkey" name="Intrusions" stroke="#ef4444" fillOpacity={1} fill="url(#colorIntrusion)" strokeWidth={2} />
                    <Area type="monotone" dataKey="clear" name="Clear Checks" stroke="#10b981" fillOpacity={1} fill="url(#colorClear)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Incident Ratio Ring */}
            <div className="bg-[#0c1221] border border-[#1e293b]/70 rounded-xl p-6 shadow-2xl flex flex-col justify-between items-center">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest w-full text-left">Intrusion vs Clear Ratio</h3>
              <div className="h-56 w-full relative flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%" cy="50%" 
                      innerRadius={65} 
                      outerRadius={85} 
                      paddingAngle={4} 
                      dataKey="value"
                      stroke="none"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                {/* Center Label */}
                <div className="absolute text-center">
                  <span className="text-3xl font-extrabold text-white block tracking-tighter">
                    {totalScans}
                  </span>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Total Scans</span>
                </div>
              </div>

              {/* Legend Block */}
              <div className="w-full grid grid-cols-2 gap-4 text-xs pt-4 border-t border-[#1e293b]">
                <div className="flex flex-col items-center p-2 bg-[#111827]/40 rounded border border-[#1e293b]/30">
                  <span className="text-red-400 font-bold text-md">{monkeyCount}</span>
                  <span className="text-slate-500 text-[10px] uppercase">Monkeys</span>
                </div>
                <div className="flex flex-col items-center p-2 bg-[#111827]/40 rounded border border-[#1e293b]/30">
                  <span className="text-emerald-400 font-bold text-md">{clearCount}</span>
                  <span className="text-slate-500 text-[10px] uppercase">Clear Checks</span>
                </div>
              </div>
            </div>

          </div>

          {/* Model Accuracy Trend Line */}
          <div className="bg-[#0c1221] border border-[#1e293b]/70 rounded-xl p-6 shadow-2xl">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">Model Confidence Score Tracking</h3>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={currentHourly} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} domain={[50, 100]} />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: '#0c1221', border: '1px solid #1e293b', borderRadius: '8px', color: '#f8fafc' }}
                  />
                  <Line type="monotone" dataKey="conf" name="Avg Confidence %" stroke="#a855f7" strokeWidth={2.5} dot={{ r: 4, strokeWidth: 1.5 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Camera Grid & Gallery */}
          <div className="bg-[#0c1221] border border-[#1e293b]/70 rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-[#1e293b] mb-6">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                Detection Feed Logs
              </h3>
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Real-time Stream</span>
              </div>
            </div>

            {filteredLogs.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredLogs.slice(0, 8).map((log, idx) => (
                  <div key={idx} className="group relative overflow-hidden rounded-lg border border-[#1e293b] bg-[#0a0f19] hover:border-slate-500 transition-all duration-300 shadow-md">
                    <div className="aspect-[4/3] bg-slate-950 relative overflow-hidden">
                      {dataMode === 'demo' ? (
                        <div className="w-full h-full flex items-center justify-center bg-slate-900 border-b border-[#1e293b]">
                          <Camera className="h-10 w-10 text-slate-600 group-hover:scale-110 transition duration-300" />
                          <span className="absolute bottom-2 left-2 text-[10px] text-slate-500 font-mono bg-black/60 px-1.5 py-0.5 rounded">Mock Frame</span>
                        </div>
                      ) : (
                        <img 
                          src={`${IMAGE_BASE}/${log.saved_image}`} 
                          alt="Intruder Capture" 
                          className="w-full h-full object-cover group-hover:scale-105 transition duration-500"
                        />
                      )}
                      
                      {/* Classification Tag Overlay */}
                      {log.result === 'monkey' ? (
                        <span className="absolute top-2 right-2 bg-red-600/90 text-white font-mono text-[10px] font-bold px-2 py-0.5 rounded shadow flex items-center gap-1 backdrop-blur-sm">
                          MONKEY {log.confidence_pct}%
                        </span>
                      ) : (
                        <span className="absolute top-2 right-2 bg-emerald-600/90 text-white font-mono text-[10px] font-bold px-2 py-0.5 rounded shadow flex items-center gap-1 backdrop-blur-sm">
                          CLEAR
                        </span>
                      )}
                    </div>

                    <div className="p-4 space-y-2">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-slate-400 font-semibold">Test Trace #{log.test_number}</span>
                        <span className="text-[10px] text-slate-600 font-mono">OK</span>
                      </div>
                      <p className="text-[10px] text-slate-500 font-mono">{log.timestamp}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-16 bg-[#0a0f19] border border-dashed border-[#1e293b] rounded-lg">
                <Activity className="h-10 w-10 text-slate-600 mx-auto mb-3 opacity-30 animate-pulse" />
                <h4 className="text-sm font-semibold text-white">No Detections Found</h4>
                <p className="text-slate-500 text-xs mt-1">Change the filter or environment mode to display data logs.</p>
              </div>
            )}
          </div>

        </div>

      </main>

    </div>
  );
}

// 20-Year BI Dev StatCard Design: Modular with customized colors
interface StatCardProps {
  title: string;
  value: number | string;
  label: string;
  theme: 'blue' | 'red' | 'emerald' | 'purple';
}

function StatCard({ title, value, label, theme }: StatCardProps) {
  const themeStyles = {
    blue: {
      border: 'border-[#38bdf8]/20 hover:border-[#38bdf8]/40',
      glow: 'shadow-[#38bdf8]/5',
      text: 'text-[#38bdf8]'
    },
    red: {
      border: 'border-red-500/20 hover:border-red-500/40',
      glow: 'shadow-red-500/5',
      text: 'text-red-500'
    },
    emerald: {
      border: 'border-emerald-500/20 hover:border-emerald-500/40',
      glow: 'shadow-emerald-500/5',
      text: 'text-emerald-500'
    },
    purple: {
      border: 'border-purple-500/20 hover:border-purple-500/40',
      glow: 'shadow-purple-500/5',
      text: 'text-purple-500'
    }
  };

  const style = themeStyles[theme];

  return (
    <div className={`bg-[#0c1221] border ${style.border} rounded-xl p-5 shadow-lg ${style.glow} transition duration-300 relative overflow-hidden group`}>
      <div className="relative z-10 flex flex-col justify-between h-full">
        <div>
          <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold block mb-1">
            {title}
          </span>
          <span className="text-3xl font-extrabold text-white tracking-tight font-mono block">
            {value}
          </span>
        </div>
        <span className={`text-[10px] font-semibold mt-4 ${style.text} tracking-wider`}>
          {label}
        </span>
      </div>
      
      {/* Power BI design touch: clean subtle top accent bar */}
      <div className={`absolute top-0 left-0 right-0 h-[2px] ${theme === 'blue' ? 'bg-[#38bdf8]' : theme === 'red' ? 'bg-red-500' : theme === 'emerald' ? 'bg-emerald-500' : 'bg-purple-500'}`}></div>
    </div>
  );
}

export default App;
