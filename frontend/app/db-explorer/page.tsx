'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  DBTableInfo,
  DBTableDetailResponse,
  DBStats,
  DBRelationshipsGraph
} from '../../lib/types';
import { api, DEMO_USERS } from '../../lib/api';
import {
  Database,
  Table,
  RefreshCw,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Layers,
  Link2,
  ExternalLink,
  Copy,
  Check,
  X,
  Eye,
  ChevronLeft,
  ChevronRight,
  Shield,
  Activity,
  HardDrive,
  Clock,
  Sparkles,
  Download,
  FileCode,
  Key,
  Network,
  Share2
} from 'lucide-react';

const CATEGORY_ICONS: Record<string, string> = {
  'CORE ORGANIZATION': '🏢',
  'PROCUREMENT CATALOG': '📦',
  'SUPPLIER MANAGEMENT': '🤝',
  'PROCUREMENT WORKFLOW': '📋',
  'RFQ & BIDDING': '⚖️',
  'PURCHASE ORDERS': '📜',
  'SYSTEM & AUDIT': '🔔',
  'OTHER': '📁'
};

export default function DatabaseExplorerPage() {
  const [stats, setStats] = useState<DBStats | null>(null);
  const [tables, setTables] = useState<DBTableInfo[]>([]);
  const [selectedTableName, setSelectedTableName] = useState<string>('purchase_requests');
  const [tableDetail, setTableDetail] = useState<DBTableDetailResponse | null>(null);
  const [relationships, setRelationships] = useState<DBRelationshipsGraph | null>(null);
  const [activeTab, setActiveTab] = useState<'data' | 'schema' | 'relationships'>('data');

  // Loading & Filter States
  const [loading, setLoading] = useState<boolean>(true);
  const [tableLoading, setTableLoading] = useState<boolean>(false);
  const [tableFilter, setTableFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);
  const [sortBy, setSortBy] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // Demo & Realtime Auto-refresh
  const [demoMode, setDemoMode] = useState<boolean>(true);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [lastRefreshed, setLastRefreshed] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Inspector Drawer State
  const [selectedRow, setSelectedRow] = useState<Record<string, any> | null>(null);

  // Initialize and ensure auth
  useEffect(() => {
    const init = async () => {
      try {
        setLoading(true);
        // Ensure admin login token if not present
        if (!api.getToken()) {
          const adminUser = DEMO_USERS.find(u => u.role === 'ADMIN') || DEMO_USERS[0];
          await api.login(adminUser.email, adminUser.password);
        }
        await Promise.all([loadStats(), loadTables(), loadRelationships()]);
        setLastRefreshed(new Date().toLocaleTimeString());
      } catch (err) {
        console.error('Initialization failed:', err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  // Auto-refresh interval if enabled
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      refreshData();
    }, 4000);
    return () => clearInterval(interval);
  }, [autoRefresh, selectedTableName, page, pageSize, searchQuery, sortBy, sortOrder]);

  // Load table details when selection, pagination, search, or sorting changes
  useEffect(() => {
    if (selectedTableName) {
      fetchTableData(selectedTableName, page, pageSize, searchQuery, sortBy, sortOrder);
    }
  }, [selectedTableName, page, pageSize, sortBy, sortOrder]);

  const loadStats = async () => {
    try {
      const data = await api.getDbStats();
      setStats(data);
    } catch (e) {
      console.error('Error loading DB stats:', e);
    }
  };

  const loadTables = async () => {
    try {
      const data = await api.getDbTables();
      setTables(data);
      if (data.length > 0 && !selectedTableName) {
        setSelectedTableName(data[0].name);
      }
    } catch (e) {
      console.error('Error loading DB tables:', e);
    }
  };

  const loadRelationships = async () => {
    try {
      const data = await api.getDbRelationships();
      setRelationships(data);
    } catch (e) {
      console.error('Error loading relationships:', e);
    }
  };

  const fetchTableData = async (
    tName: string,
    p: number,
    pSize: number,
    search?: string,
    sortCol?: string,
    sortDir?: 'asc' | 'desc'
  ) => {
    try {
      setTableLoading(true);
      const res = await api.getDbTableDetail(tName, p, pSize, search, sortCol, sortDir);
      setTableDetail(res);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (e) {
      console.error('Error loading table detail:', e);
    } finally {
      setTableLoading(false);
    }
  };

  const refreshData = async () => {
    await Promise.all([
      loadStats(),
      loadTables(),
      fetchTableData(selectedTableName, page, pageSize, searchQuery, sortBy, sortOrder)
    ]);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTableData(selectedTableName, 1, pageSize, searchQuery, sortBy, sortOrder);
  };

  const handleSort = (colName: string) => {
    if (sortBy === colName) {
      setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(colName);
      setSortOrder('asc');
    }
  };

  const handleSelectTable = (tName: string) => {
    setSelectedTableName(tName);
    setPage(1);
    setSearchQuery('');
    setSortBy('');
    setSelectedRow(null);
  };

  const copyToClipboard = (text: string, keyId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyId);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const exportTableAsJSON = () => {
    if (!tableDetail || !tableDetail.rows) return;
    const blob = new Blob([JSON.stringify(tableDetail.rows, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedTableName}_records_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportTableAsCSV = () => {
    if (!tableDetail || !tableDetail.rows || tableDetail.rows.length === 0) return;
    const cols = tableDetail.columns.map(c => c.name);
    const csvRows = [
      cols.join(','),
      ...tableDetail.rows.map(row =>
        cols
          .map(col => {
            const val = row[col];
            if (val === null || val === undefined) return '""';
            const str = typeof val === 'object' ? JSON.stringify(val) : String(val);
            return `"${str.replace(/"/g, '""')}"`;
          })
          .join(',')
      )
    ];
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedTableName}_records_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Group tables by category
  const groupedTables = useMemo(() => {
    const filtered = tables.filter(t =>
      t.name.toLowerCase().includes(tableFilter.toLowerCase()) ||
      t.category.toLowerCase().includes(tableFilter.toLowerCase())
    );

    const groups: Record<string, DBTableInfo[]> = {};
    filtered.forEach(t => {
      const cat = t.category || 'OTHER';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(t);
    });
    return groups;
  }, [tables, tableFilter]);

  // Format cell values cleanly
  const renderCellContent = (val: any, colName: string, isPk: boolean) => {
    if (val === null || val === undefined) {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-slate-800 text-slate-500 border border-slate-700/60">
          NULL
        </span>
      );
    }

    if (typeof val === 'boolean') {
      return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
          val ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60' : 'bg-rose-950/80 text-rose-400 border border-rose-800/60'
        }`}>
          {val ? 'TRUE' : 'FALSE'}
        </span>
      );
    }

    if (typeof val === 'object') {
      const jsonStr = JSON.stringify(val);
      const isArray = Array.isArray(val);
      return (
        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-300 font-mono text-[11px] border border-cyan-800/40 max-w-[200px] truncate" title={jsonStr}>
          <FileCode className="w-3 h-3 text-cyan-400 shrink-0" />
          <span className="truncate">{isArray ? `[${val.length} items]` : `{${Object.keys(val).length} keys}`}</span>
        </span>
      );
    }

    const strVal = String(val);

    // Format UUIDs cleanly
    if (strVal.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)) {
      return (
        <span className="font-mono text-[11px] text-cyan-300 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/60" title={strVal}>
          {strVal.slice(0, 8)}…{strVal.slice(-4)}
        </span>
      );
    }

    // Format status strings
    const statusValues = ['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'REVISION_REQUIRED', 'RFQS_ISSUED', 'AWAITING_QUOTATIONS', 'QUOTATIONS_READY', 'APPROVED', 'PO_GENERATED', 'COMPLETED', 'REJECTED', 'PENDING', 'ISSUED', 'ACCEPTED', 'ACTIVE'];
    if (statusValues.includes(strVal.toUpperCase())) {
      let color = 'bg-blue-950/80 text-blue-400 border-blue-800/60';
      if (strVal.includes('APPROVED') || strVal.includes('COMPLETED') || strVal.includes('ACTIVE')) color = 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60';
      if (strVal.includes('REJECTED')) color = 'bg-rose-950/80 text-rose-400 border-rose-800/60';
      if (strVal.includes('REVIEW') || strVal.includes('PENDING')) color = 'bg-amber-950/80 text-amber-400 border-amber-800/60';
      if (strVal.includes('REVISION')) color = 'bg-purple-950/80 text-purple-400 border-purple-800/60';

      return (
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold tracking-wide border ${color}`}>
          {strVal}
        </span>
      );
    }

    // Format ISO Datetime strings
    if (strVal.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
      const d = new Date(strVal);
      return (
        <span className="font-mono text-xs text-slate-300 whitespace-nowrap" title={strVal}>
          {d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
      );
    }

    return <span className="text-slate-200 text-xs truncate max-w-xs block" title={strVal}>{strVal}</span>;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* TOP HEADER */}
      <header className="bg-slate-900/90 border-b border-slate-800 sticky top-0 z-40 backdrop-blur-md px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        {/* Brand & System Title */}
        <div className="flex items-center space-x-4">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 border border-cyan-400/30">
            <Database className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-black tracking-wider text-base text-white">IPMS</span>
              <span className="font-semibold text-base text-cyan-400 tracking-wide">DATABASE EXPLORER</span>
              <span className="bg-cyan-950/90 border border-cyan-800/60 text-cyan-300 font-mono text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                Dev / Demo Tool
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">
              Live Relational Database Inspection Console & Real-Time Persistence Verifier
            </p>
          </div>
        </div>

        {/* Database Status & Live Diagnostics */}
        <div className="flex items-center space-x-6 text-xs text-slate-300">
          <div className="flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="font-bold text-emerald-400 tracking-wide">LIVE DATABASE CONNECTION</span>
            <span className="text-slate-500">|</span>
            <span className="font-mono text-slate-300">{stats?.database_type.split(' (')[0] || 'SQLite 3'}</span>
          </div>

          <div className="hidden lg:flex items-center space-x-4 text-[11px] text-slate-400">
            <div className="flex items-center space-x-1.5">
              <HardDrive className="w-3.5 h-3.5 text-slate-500" />
              <span>File: <strong className="text-slate-200 font-mono">{stats?.database_file || 'procurement.db'}</strong> ({stats?.file_size_formatted || '320 KB'})</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>Refreshed: <strong className="text-slate-200 font-mono">{lastRefreshed || 'Just now'}</strong></span>
            </div>
          </div>
        </div>

        {/* Top Actions & Demo Toggles */}
        <div className="flex items-center space-x-3">
          {/* Demo Mode Badge */}
          <div className="flex items-center space-x-2 bg-gradient-to-r from-amber-500/10 to-amber-600/20 border border-amber-500/30 px-3 py-1.5 rounded-lg">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-xs font-bold text-amber-300">LIVE DEMO MODE</span>
          </div>

          {/* Auto Refresh Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg border transition ${
              autoRefresh
                ? 'bg-emerald-950/80 text-emerald-300 border-emerald-700/80 shadow-sm shadow-emerald-900/40'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200'
            }`}
            title="Auto-refresh tables every 4 seconds when performing actions in IPMS"
          >
            <Activity className={`w-3.5 h-3.5 ${autoRefresh ? 'text-emerald-400 animate-spin' : 'text-slate-500'}`} />
            <span>{autoRefresh ? 'Auto-Polling: ON' : 'Auto-Poll: OFF'}</span>
          </button>

          {/* Refresh Database Button */}
          <button
            onClick={refreshData}
            disabled={tableLoading}
            className="flex items-center space-x-2 bg-cyan-600 hover:bg-cyan-500 active:bg-cyan-700 text-white text-xs font-bold px-4 py-1.5 rounded-lg shadow-md shadow-cyan-900/30 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${tableLoading ? 'animate-spin' : ''}`} />
            <span>REFRESH DATABASE</span>
          </button>
        </div>
      </header>

      {/* BODY CONTENT - SIDEBAR + MAIN VIEW */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT SIDEBAR: TABLES NAVIGATION */}
        <aside className="w-72 bg-slate-900/70 border-r border-slate-800/80 flex flex-col shrink-0">
          {/* Table Search & Meta Summary */}
          <div className="p-3.5 border-b border-slate-800/80 space-y-2.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-bold tracking-wider uppercase text-[11px] text-slate-400">Database Tables</span>
              <span className="bg-slate-800 text-cyan-400 font-mono text-[11px] font-bold px-2 py-0.5 rounded border border-slate-700/60">
                {tables.length} Tables | {stats?.total_records ?? 0} Records
              </span>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                value={tableFilter}
                onChange={e => setTableFilter(e.target.value)}
                placeholder="Filter table names..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500 transition"
              />
              {tableFilter && (
                <button onClick={() => setTableFilter('')} className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Grouped Table List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-4 custom-scrollbar">
            {Object.entries(groupedTables).map(([category, catTables]) => (
              <div key={category} className="space-y-1">
                <div className="px-2.5 py-1 text-[10px] font-bold tracking-wider uppercase text-slate-500 flex items-center space-x-1.5">
                  <span>{CATEGORY_ICONS[category] || '📁'}</span>
                  <span>{category}</span>
                </div>

                <div className="space-y-0.5">
                  {catTables.map(t => {
                    const isSelected = selectedTableName === t.name;
                    return (
                      <button
                        key={t.name}
                        onClick={() => handleSelectTable(t.name)}
                        className={`w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-xs font-mono transition text-left ${
                          isSelected
                            ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-700/60 shadow-sm font-semibold'
                            : 'text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent'
                        }`}
                      >
                        <div className="flex items-center space-x-2 truncate">
                          <Table className={`w-3.5 h-3.5 shrink-0 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
                          <span className="truncate">{t.name}</span>
                        </div>
                        <span className={`px-1.5 py-0.5 text-[10px] rounded font-mono font-bold shrink-0 ml-2 ${
                          isSelected
                            ? 'bg-cyan-500 text-slate-950'
                            : t.row_count > 0
                            ? 'bg-slate-800 text-slate-300 border border-slate-700/60'
                            : 'bg-slate-900/50 text-slate-600'
                        }`}>
                          {t.row_count}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Sidebar Footer Integrity Info */}
          <div className="p-3 bg-slate-950/80 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="w-3.5 h-3.5 text-cyan-400" />
              <span>ACID Persistence</span>
            </div>
            <span className="text-[10px] font-mono text-emerald-400">Strict Read-Only</span>
          </div>
        </aside>

        {/* MAIN VIEW AREA */}
        <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
          {/* Table Header & Controls Bar */}
          <div className="bg-slate-900/50 border-b border-slate-800/80 px-6 py-4 flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-4">
              {/* Table Name & Meta Chips */}
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-lg bg-cyan-950 border border-cyan-800/60 flex items-center justify-center text-cyan-400 font-bold">
                  ▦
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h2 className="text-lg font-bold text-white font-mono tracking-tight">{selectedTableName}</h2>
                    <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">
                      {tableDetail?.category || 'TABLE'}
                    </span>
                  </div>
                  <div className="flex items-center space-x-3 text-xs text-slate-400 font-mono mt-0.5">
                    <span>Rows: <strong className="text-cyan-400">{tableDetail?.total_rows ?? 0}</strong></span>
                    <span>•</span>
                    <span>Columns: <strong className="text-slate-200">{tableDetail?.columns.length ?? 0}</strong></span>
                    <span>•</span>
                    <span>PK: <strong className="text-amber-400">{tableDetail?.primary_key || 'id'}</strong></span>
                    {tableDetail?.foreign_keys && tableDetail.foreign_keys.length > 0 && (
                      <>
                        <span>•</span>
                        <span>Outbound FKs: <strong className="text-blue-400">{tableDetail.foreign_keys.length}</strong></span>
                      </>
                    )}
                    {tableDetail?.inbound_foreign_keys && tableDetail.inbound_foreign_keys.length > 0 && (
                      <>
                        <span>•</span>
                        <span>Referenced By: <strong className="text-emerald-400">{tableDetail.inbound_foreign_keys.length} tables</strong></span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* View Tabs (Data, Schema, Relationships) & Exports */}
              <div className="flex items-center space-x-3">
                {/* View Tabs */}
                <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800">
                  <button
                    onClick={() => setActiveTab('data')}
                    className={`flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold transition ${
                      activeTab === 'data'
                        ? 'bg-cyan-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Table className="w-3.5 h-3.5" />
                    <span>Table Data</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('schema')}
                    className={`flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold transition ${
                      activeTab === 'schema'
                        ? 'bg-cyan-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Columns & Types</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('relationships')}
                    className={`flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-semibold transition ${
                      activeTab === 'relationships'
                        ? 'bg-cyan-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Network className="w-3.5 h-3.5" />
                    <span>Relationships</span>
                  </button>
                </div>

                {/* Export Buttons */}
                <div className="flex items-center space-x-1.5">
                  <button
                    onClick={exportTableAsJSON}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 text-xs font-medium transition flex items-center space-x-1"
                    title="Export table records as JSON"
                  >
                    <Download className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-[11px]">JSON</span>
                  </button>
                  <button
                    onClick={exportTableAsCSV}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 text-xs font-medium transition flex items-center space-x-1"
                    title="Export table records as CSV"
                  >
                    <Download className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-[11px]">CSV</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Filter, Search & Pagination Controls (when on data tab) */}
            {activeTab === 'data' && (
              <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/60">
                {/* Search Form */}
                <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      placeholder={`Search across ${selectedTableName}...`}
                      className="w-64 bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-8 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-cyan-500 transition"
                    />
                    {searchQuery && (
                      <button
                        type="button"
                        onClick={() => {
                          setSearchQuery('');
                          fetchTableData(selectedTableName, 1, pageSize, '', sortBy, sortOrder);
                        }}
                        className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <button
                    type="submit"
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition"
                  >
                    Filter
                  </button>
                </form>

                {/* Pagination Controls */}
                <div className="flex items-center space-x-3 text-xs text-slate-400 font-mono">
                  {/* Page Size */}
                  <div className="flex items-center space-x-1.5">
                    <span>Page Size:</span>
                    <select
                      value={pageSize}
                      onChange={e => {
                        const newSize = Number(e.target.value);
                        setPageSize(newSize);
                        setPage(1);
                      }}
                      className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded px-2 py-1 focus:outline-none focus:border-cyan-500"
                    >
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>

                  <span>
                    Page <strong>{tableDetail?.page ?? 1}</strong> of <strong>{tableDetail?.total_pages ?? 1}</strong> ({tableDetail?.total_rows ?? 0} total)
                  </span>

                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => setPage(prev => Math.max(prev - 1, 1))}
                      disabled={!tableDetail?.has_prev || tableLoading}
                      className="p-1 bg-slate-950 hover:bg-slate-800 disabled:opacity-30 rounded border border-slate-800 text-slate-300 transition"
                      title="Previous Page"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setPage(prev => (tableDetail?.has_next ? prev + 1 : prev))}
                      disabled={!tableDetail?.has_next || tableLoading}
                      className="p-1 bg-slate-950 hover:bg-slate-800 disabled:opacity-30 rounded border border-slate-800 text-slate-300 transition"
                      title="Next Page"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* TAB 1: INTERACTIVE DATA GRID */}
          {activeTab === 'data' && (
            <div className="flex-1 overflow-auto custom-scrollbar relative">
              {tableLoading ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-3">
                  <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
                  <p className="text-xs font-mono">Querying relational records for {selectedTableName}...</p>
                </div>
              ) : !tableDetail || tableDetail.rows.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4 p-8 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 shadow-inner">
                    <Database className="w-7 h-7 text-cyan-400/80" />
                  </div>
                  <div className="max-w-md space-y-1.5">
                    <h3 className="text-base font-bold text-slate-200 font-mono">
                      {selectedTableName} is Currently Empty (0 Records)
                    </h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {searchQuery
                        ? `No records found matching query "${searchQuery}".`
                        : `All request tables were cleared for a fresh demo run. Once you create a Purchase Request in the IPMS app, records will immediately persist and display here!`}
                    </p>
                  </div>

                  {/* Quick-switch to populated catalog/org tables */}
                  <div className="pt-2 flex flex-wrap items-center justify-center gap-2">
                    <span className="text-[11px] text-slate-500 font-medium">Inspect populated tables:</span>
                    <button
                      onClick={() => handleSelectTable('items')}
                      className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-cyan-300 rounded-md border border-slate-700 text-xs font-mono font-medium transition"
                    >
                      items (9)
                    </button>
                    <button
                      onClick={() => handleSelectTable('vendors')}
                      className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-cyan-300 rounded-md border border-slate-700 text-xs font-mono font-medium transition"
                    >
                      vendors (9)
                    </button>
                    <button
                      onClick={() => handleSelectTable('users')}
                      className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-cyan-300 rounded-md border border-slate-700 text-xs font-mono font-medium transition"
                    >
                      users (14)
                    </button>
                    <button
                      onClick={() => handleSelectTable('inventory')}
                      className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-cyan-300 rounded-md border border-slate-700 text-xs font-mono font-medium transition"
                    >
                      inventory (9)
                    </button>
                    <button
                      onClick={() => handleSelectTable('vendor_reviews')}
                      className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-cyan-300 rounded-md border border-slate-700 text-xs font-mono font-medium transition"
                    >
                      vendor_reviews (72)
                    </button>
                  </div>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead className="bg-slate-900/90 text-slate-400 text-[11px] font-mono uppercase tracking-wider sticky top-0 z-20 border-b border-slate-800 backdrop-blur-sm">
                    <tr>
                      <th className="py-2.5 px-3 w-12 text-center text-slate-600 border-r border-slate-800/60 font-bold">#</th>
                      {tableDetail.columns.map(col => {
                        const isPk = col.pk;
                        const isSorted = sortBy === col.name;
                        return (
                          <th
                            key={col.name}
                            onClick={() => handleSort(col.name)}
                            className="py-2.5 px-4 font-semibold hover:text-white cursor-pointer select-none transition border-r border-slate-800/40 whitespace-nowrap"
                          >
                            <div className="flex items-center space-x-1.5">
                              {isPk && <Key className="w-3 h-3 text-amber-400 shrink-0" />}
                              <span>{col.name}</span>
                              <span className="text-[9px] text-slate-500 font-normal lowercase">({col.type})</span>
                              {isSorted ? (
                                sortOrder === 'asc' ? (
                                  <ArrowUp className="w-3 h-3 text-cyan-400" />
                                ) : (
                                  <ArrowDown className="w-3 h-3 text-cyan-400" />
                                )
                              ) : (
                                <ArrowUpDown className="w-2.5 h-2.5 text-slate-600 opacity-0 group-hover:opacity-100" />
                              )}
                            </div>
                          </th>
                        );
                      })}
                      <th className="py-2.5 px-3 w-16 text-center text-slate-500 font-semibold">Inspect</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-sans text-xs">
                    {tableDetail.rows.map((row, idx) => {
                      const rowNum = (page - 1) * pageSize + idx + 1;
                      const pkVal = row[tableDetail.primary_key];
                      const isRowSelected = selectedRow && selectedRow[tableDetail.primary_key] === pkVal;

                      return (
                        <tr
                          key={pkVal ? String(pkVal) : idx}
                          onClick={() => setSelectedRow(row)}
                          className={`hover:bg-slate-900/80 cursor-pointer transition ${
                            isRowSelected ? 'bg-cyan-950/40 ring-1 ring-cyan-500/40' : idx % 2 === 0 ? 'bg-slate-950' : 'bg-slate-900/30'
                          }`}
                        >
                          <td className="py-2 px-3 text-center text-[11px] font-mono text-slate-500 border-r border-slate-800/60">
                            {rowNum}
                          </td>
                          {tableDetail.columns.map(col => (
                            <td
                              key={col.name}
                              className="py-2 px-4 border-r border-slate-800/40 max-w-xs truncate align-middle"
                            >
                              {renderCellContent(row[col.name], col.name, col.pk)}
                            </td>
                          ))}
                          <td className="py-2 px-3 text-center">
                            <button
                              onClick={e => {
                                e.stopPropagation();
                                setSelectedRow(row);
                              }}
                              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-cyan-300 transition"
                              title="Inspect record details"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* TAB 2: SCHEMA & COLUMNS VIEW */}
          {activeTab === 'schema' && tableDetail && (
            <div className="flex-1 overflow-auto p-6 space-y-6 custom-scrollbar">
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-white font-mono flex items-center space-x-2">
                      <Layers className="w-4 h-4 text-cyan-400" />
                      <span>Schema Definition for "{tableDetail.table}"</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Columns, data types, nullability, default values, and primary keys.
                    </p>
                  </div>
                  <span className="text-xs font-mono text-cyan-400 bg-slate-950 px-3 py-1 rounded-lg border border-slate-800">
                    {tableDetail.columns.length} Total Columns
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono border-collapse">
                    <thead className="bg-slate-950 text-slate-400 uppercase text-[10px] tracking-wider border-b border-slate-800">
                      <tr>
                        <th className="py-2 px-3">Column Name</th>
                        <th className="py-2 px-3">Data Type</th>
                        <th className="py-2 px-3">Key Type</th>
                        <th className="py-2 px-3">Nullable</th>
                        <th className="py-2 px-3">Default Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {tableDetail.columns.map(col => (
                        <tr key={col.name} className="hover:bg-slate-800/40 transition">
                          <td className="py-2.5 px-3 font-bold text-slate-200 flex items-center space-x-2">
                            {col.pk && <Key className="w-3.5 h-3.5 text-amber-400" />}
                            <span>{col.name}</span>
                          </td>
                          <td className="py-2.5 px-3 text-cyan-400">{col.type}</td>
                          <td className="py-2.5 px-3">
                            {col.pk ? (
                              <span className="bg-amber-950 text-amber-400 px-2 py-0.5 rounded text-[10px] font-bold border border-amber-800/60">
                                PRIMARY KEY
                              </span>
                            ) : (
                              <span className="text-slate-600">-</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3">
                            {col.notnull ? (
                              <span className="text-rose-400 font-semibold">NOT NULL</span>
                            ) : (
                              <span className="text-emerald-400">NULLABLE</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-slate-400">
                            {col.dflt_value !== null && col.dflt_value !== undefined ? (
                              String(col.dflt_value)
                            ) : (
                              <span className="text-slate-600">None</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: RELATIONSHIPS VISUALIZER */}
          {activeTab === 'relationships' && tableDetail && (
            <div className="flex-1 overflow-auto p-6 space-y-6 custom-scrollbar">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Outbound Foreign Keys */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white font-mono flex items-center space-x-2">
                      <Link2 className="w-4 h-4 text-blue-400" />
                      <span>Outbound References ({tableDetail.table} → Other)</span>
                    </h3>
                    <span className="text-xs font-mono text-blue-400 bg-slate-950 px-2.5 py-0.5 rounded border border-slate-800">
                      {tableDetail.foreign_keys.length} FKs
                    </span>
                  </div>

                  {tableDetail.foreign_keys.length === 0 ? (
                    <p className="text-xs text-slate-500 font-mono py-4">No outbound foreign key references defined.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {tableDetail.foreign_keys.map((fk, idx) => (
                        <div
                          key={idx}
                          onClick={() => handleSelectTable(fk.to_table)}
                          className="bg-slate-950 hover:bg-slate-900 p-3 rounded-lg border border-slate-800 hover:border-cyan-500/50 cursor-pointer transition flex items-center justify-between group"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center space-x-2 font-mono text-xs">
                              <span className="text-amber-300 font-bold">{fk.from_column}</span>
                              <span className="text-slate-500">→</span>
                              <span className="text-cyan-400 font-bold group-hover:underline">{fk.to_table}</span>
                              <span className="text-slate-500">({fk.to_column})</span>
                            </div>
                            <div className="text-[10px] text-slate-500">
                              ON DELETE: {fk.on_delete || 'NO ACTION'} | ON UPDATE: {fk.on_update || 'NO ACTION'}
                            </div>
                          </div>
                          <ExternalLink className="w-4 h-4 text-slate-600 group-hover:text-cyan-400 transition" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Inbound Foreign Keys */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white font-mono flex items-center space-x-2">
                      <Share2 className="w-4 h-4 text-emerald-400" />
                      <span>Inbound References (Referenced By Other Tables)</span>
                    </h3>
                    <span className="text-xs font-mono text-emerald-400 bg-slate-950 px-2.5 py-0.5 rounded border border-slate-800">
                      {tableDetail.inbound_foreign_keys.length} Dependent Tables
                    </span>
                  </div>

                  {tableDetail.inbound_foreign_keys.length === 0 ? (
                    <p className="text-xs text-slate-500 font-mono py-4">No other tables currently reference this table directly.</p>
                  ) : (
                    <div className="space-y-2.5">
                      {tableDetail.inbound_foreign_keys.map((ifk, idx) => (
                        <div
                          key={idx}
                          onClick={() => handleSelectTable(ifk.from_table)}
                          className="bg-slate-950 hover:bg-slate-900 p-3 rounded-lg border border-slate-800 hover:border-emerald-500/50 cursor-pointer transition flex items-center justify-between group"
                        >
                          <div className="flex items-center space-x-2 font-mono text-xs">
                            <span className="text-emerald-400 font-bold group-hover:underline">{ifk.from_table}</span>
                            <span className="text-slate-500 font-normal">({ifk.from_column})</span>
                            <span className="text-slate-500">→</span>
                            <span className="text-slate-300">{tableDetail.table} ({ifk.to_column})</span>
                          </div>
                          <ExternalLink className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 transition" />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>

        {/* RIGHT SIDEBAR: ROW INSPECTOR DRAWER */}
        {selectedRow && tableDetail && (
          <aside className="w-96 bg-slate-900 border-l border-slate-800 flex flex-col shrink-0 shadow-2xl z-30 animate-in slide-in-from-right-10 duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <Eye className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-bold text-sm text-white font-mono uppercase">Record Inspector</h3>
                </div>
                <p className="text-[11px] text-slate-400 font-mono">
                  Table: <strong className="text-slate-200">{tableDetail.table}</strong>
                </p>
              </div>
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => copyToClipboard(JSON.stringify(selectedRow, null, 2), 'drawer_row')}
                  className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-cyan-300 transition"
                  title="Copy full record JSON"
                >
                  {copiedKey === 'drawer_row' ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => setSelectedRow(null)}
                  className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition"
                  title="Close inspector"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Record Fields List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
              {tableDetail.columns.map(col => {
                const val = selectedRow[col.name];
                const isPk = col.pk;
                const isObject = typeof val === 'object' && val !== null;

                return (
                  <div key={col.name} className="space-y-1.5 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-300 flex items-center space-x-1.5">
                        {isPk && <Key className="w-3 h-3 text-amber-400" />}
                        <span>{col.name}</span>
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 uppercase">{col.type}</span>
                    </div>

                    {isObject ? (
                      <div className="mt-1">
                        <pre className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-[11px] text-cyan-300 overflow-x-auto max-h-48 custom-scrollbar">
                          {JSON.stringify(val, null, 2)}
                        </pre>
                      </div>
                    ) : (
                      <div className="font-mono text-xs text-slate-100 break-all select-all">
                        {val === null || val === undefined ? (
                          <span className="text-slate-600 italic">NULL</span>
                        ) : (
                          String(val)
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Drawer Footer */}
            <div className="p-3 bg-slate-950 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
              <span>Read-Only Relational Inspection</span>
              <span className="font-mono text-slate-400">PostgreSQL / SQLite</span>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
