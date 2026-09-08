'use client';

import React, { useState, useEffect } from 'react';
import { DBTableInfo, DBTableData, SQLQueryResult } from '../lib/types';
import { api } from '../lib/api';
import {
  Database,
  Table,
  Search,
  RefreshCw,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  Play,
  Terminal,
  AlertCircle,
  CheckCircle2,
  Layers,
  Sparkles,
  Zap,
  ArrowRight,
  Filter,
  Save
} from 'lucide-react';

interface DatabaseExplorerProps {
  onDataChanged?: () => void;
}

export const DatabaseExplorer: React.FC<DatabaseExplorerProps> = ({ onDataChanged }) => {
  const [tables, setTables] = useState<DBTableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>('inventory');
  const [tableData, setTableData] = useState<DBTableData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // In-line / Modal editing state
  const [editingRecord, setEditingRecord] = useState<Record<string, any> | null>(null);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [newRowData, setNewRowData] = useState<Record<string, any>>({});
  const [isSaving, setIsSaving] = useState<boolean>(false);

  // SQL Console state
  const [showSqlConsole, setShowSqlConsole] = useState<boolean>(false);
  const [sqlQuery, setSqlQuery] = useState<string>('SELECT item_id, available_quantity FROM inventory;');
  const [sqlResult, setSqlResult] = useState<SQLQueryResult | null>(null);
  const [sqlRunning, setSqlRunning] = useState<boolean>(false);

  // Load all table list on mount
  useEffect(() => {
    loadTables();
  }, []);

  // Load table records whenever selectedTable or search changes
  useEffect(() => {
    if (selectedTable) {
      loadTableData(selectedTable, searchQuery);
    }
  }, [selectedTable]);

  const loadTables = async () => {
    try {
      const list = await api.getDbTables();
      setTables(list);
    } catch (err: any) {
      console.error('Failed to load DB tables:', err);
    }
  };

  const loadTableData = async (tableName: string, search = '') => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const data = await api.getDbTableData(tableName, 100, 0, search);
      setTableData(data);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to fetch table data.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedTable) {
      loadTableData(selectedTable, searchQuery);
    }
  };

  const handleEditClick = (record: Record<string, any>) => {
    setEditingRecord({ ...record });
    setIsCreating(false);
  };

  const handleSaveEdit = async () => {
    if (!editingRecord || !tableData) return;
    const pk = tableData.primary_key;
    const rowId = editingRecord[pk];
    if (!rowId) {
      setStatusMessage({ type: 'error', text: `Missing primary key (${pk}) value.` });
      return;
    }

    setIsSaving(true);
    setStatusMessage(null);
    try {
      await api.updateDbTableRow(selectedTable, String(rowId), editingRecord);
      setStatusMessage({ type: 'success', text: `Successfully updated record (${pk}: ${rowId}) in ${selectedTable}!` });
      setEditingRecord(null);
      await loadTableData(selectedTable, searchQuery);
      await loadTables();
      if (onDataChanged) onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to update record.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreateRow = async () => {
    if (!tableData) return;
    setIsSaving(true);
    setStatusMessage(null);
    try {
      await api.createDbTableRow(selectedTable, newRowData);
      setStatusMessage({ type: 'success', text: `Successfully added new record into ${selectedTable}!` });
      setIsCreating(false);
      setNewRowData({});
      await loadTableData(selectedTable, searchQuery);
      await loadTables();
      if (onDataChanged) onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to create record.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteRow = async (rowId: string) => {
    if (!tableData) return;
    const pk = tableData.primary_key;
    if (!confirm(`Are you sure you want to delete record where ${pk} = '${rowId}' from ${selectedTable}?`)) {
      return;
    }

    try {
      await api.deleteDbTableRow(selectedTable, rowId);
      setStatusMessage({ type: 'success', text: `Deleted record from ${selectedTable}.` });
      await loadTableData(selectedTable, searchQuery);
      await loadTables();
      if (onDataChanged) onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to delete record.' });
    }
  };

  const handleRunSql = async () => {
    if (!sqlQuery.trim()) return;
    setSqlRunning(true);
    setSqlResult(null);
    setStatusMessage(null);
    try {
      const res = await api.executeRawSql(sqlQuery);
      setSqlResult(res);
      if (res.type === 'MUTATION') {
        setStatusMessage({ type: 'success', text: res.message || 'SQL executed successfully.' });
        await loadTableData(selectedTable, searchQuery);
        await loadTables();
        if (onDataChanged) onDataChanged();
      }
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'SQL Execution failed.' });
    } finally {
      setSqlRunning(false);
    }
  };

  // ── Quick Action Presets ───────────────────────────────────────────────────
  const runPreset = async (name: string, query: string) => {
    setSqlQuery(query);
    setShowSqlConsole(true);
    setSqlRunning(true);
    setStatusMessage(null);
    try {
      const res = await api.executeRawSql(query);
      setSqlResult(res);
      setStatusMessage({ type: 'success', text: `Preset "${name}" executed! (${res.affected_rows ?? res.row_count ?? 0} affected)` });
      await loadTableData(selectedTable, searchQuery);
      await loadTables();
      if (onDataChanged) onDataChanged();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Preset execution failed.' });
    } finally {
      setSqlRunning(false);
    }
  };

  const friendlyTableLabels: Record<string, string> = {
    inventory: '📦 Inventory Stock',
    items: '🏷️ Product Catalog',
    vendors: '🏢 Suppliers & Vendors',
    vendor_performance: '📊 Vendor Performance Scores',
    vendor_reviews: '⭐ Google Form Vendor Reviews',
    purchase_requests: '📝 Purchase Requests',
    rfqs: '📨 RFQs (Dispatched)',
    quotations: '💰 Vendor Quotations',
    purchase_orders: '📜 Purchase Orders',
    users: '👤 User Accounts',
    departments: '🏛️ Departments',
    historical_prices: '📈 Historical Price Records',
    pr_recommendation_snapshots: '🤖 AI Recommendation Snapshots',
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-purple-100 text-purple-700 rounded-xl">
              <Database className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-bold text-slate-900">Database & Live Data Explorer</h2>
                <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 border border-emerald-300 rounded text-[10px] font-extrabold flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>LIVE SQLite Direct Sync</span>
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Inspect, modify, or insert live records across all procurement database tables. Any change immediately reflects in live inventory and recommendation checks.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={() => setShowSqlConsole(v => !v)}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 border ${
                showSqlConsole
                  ? 'bg-purple-600 text-white border-purple-600 shadow-md shadow-purple-600/20'
                  : 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100'
              }`}
            >
              <Terminal className="w-4 h-4" />
              <span>{showSqlConsole ? 'Hide SQL Console' : 'Open SQL Console'}</span>
            </button>
            <button
              onClick={() => { loadTables(); loadTableData(selectedTable, searchQuery); }}
              className="p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-100 transition"
              title="Refresh Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Quick Testing Presets */}
        <div className="pt-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="font-bold text-slate-500 flex items-center space-x-1 text-[11px]">
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            <span>Quick Test Presets:</span>
          </span>

          <button
            onClick={() => runPreset('Set Herman Miller Stock to 0', "UPDATE inventory SET available_quantity = 0 WHERE item_id IN (SELECT id FROM items WHERE name LIKE '%Herman Miller%');")}
            className="px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 rounded-lg text-[11px] font-semibold transition"
          >
            Set Herman Miller Stock = 0 (Shortage)
          </button>

          <button
            onClick={() => runPreset('Set Herman Miller Stock to 100', "UPDATE inventory SET available_quantity = 100 WHERE item_id IN (SELECT id FROM items WHERE name LIKE '%Herman Miller%');")}
            className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 rounded-lg text-[11px] font-semibold transition"
          >
            Set Herman Miller Stock = 100 (Sufficient)
          </button>

          <button
            onClick={() => runPreset('Reset All Stock to 25', "UPDATE inventory SET available_quantity = 25;")}
            className="px-2.5 py-1 bg-blue-50 hover:bg-blue-100 text-blue-800 border border-blue-200 rounded-lg text-[11px] font-semibold transition"
          >
            Reset All Stock = 25 Units
          </button>

          <button
            onClick={() => runPreset('Boost Apex Tech Quality Score', "UPDATE vendor_performance SET quality_score = 98.0 WHERE vendor_id IN (SELECT id FROM vendors WHERE name LIKE '%Apex%');")}
            className="px-2.5 py-1 bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 rounded-lg text-[11px] font-semibold transition"
          >
            Boost Apex Tech Quality = 98%
          </button>
        </div>
      </div>

      {/* Status Messages */}
      {statusMessage && (
        <div className={`p-4 rounded-xl text-xs flex items-center space-x-2 border ${
          statusMessage.type === 'success'
            ? 'bg-emerald-50 text-emerald-900 border-emerald-200'
            : 'bg-rose-50 text-rose-900 border-rose-200'
        }`}>
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          )}
          <span className="font-medium">{statusMessage.text}</span>
        </div>
      )}

      {/* Raw SQL Terminal Console */}
      {showSqlConsole && (
        <div className="bg-slate-900 text-slate-100 rounded-2xl p-5 shadow-xl border border-slate-800 space-y-3 font-mono text-xs animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center space-x-2 text-purple-400 font-bold">
              <Terminal className="w-4 h-4" />
              <span>Direct SQLite SQL Terminal</span>
            </div>
            <span className="text-[10px] text-slate-400">Target DB: procurement.db</span>
          </div>

          <div className="space-y-2">
            <textarea
              rows={3}
              value={sqlQuery}
              onChange={e => setSqlQuery(e.target.value)}
              placeholder="Enter SQLite query (e.g. SELECT * FROM inventory; or UPDATE ...)"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-emerald-400 font-mono focus:ring-2 focus:ring-purple-500 focus:outline-none"
            />
            <div className="flex justify-between items-center">
              <span className="text-[10px] text-slate-500">Supports SELECT, UPDATE, INSERT, DELETE, PRAGMA</span>
              <button
                onClick={handleRunSql}
                disabled={sqlRunning}
                className="px-4 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-bold flex items-center space-x-1.5 transition disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>{sqlRunning ? 'Executing...' : 'Run SQL'}</span>
              </button>
            </div>
          </div>

          {sqlResult && (
            <div className="mt-3 p-3 bg-slate-950 rounded-xl border border-slate-800 overflow-x-auto max-h-60">
              {sqlResult.type === 'SELECT' && sqlResult.results && (
                <div>
                  <div className="text-[10px] text-slate-400 mb-1">
                    Returned {sqlResult.row_count} row(s):
                  </div>
                  <table className="w-full text-left text-[11px]">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        {sqlResult.columns?.map(c => (
                          <th key={c} className="py-1 px-2">{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900 text-slate-300">
                      {sqlResult.results.map((r, i) => (
                        <tr key={i} className="hover:bg-slate-900/60">
                          {sqlResult.columns?.map(c => (
                            <td key={c} className="py-1 px-2 whitespace-nowrap">{String(r[c] ?? 'NULL')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {sqlResult.type === 'MUTATION' && (
                <div className="text-emerald-400 font-bold">
                  ✓ {sqlResult.message}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Main Table Explorer Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Table Selector Sidebar */}
        <div className="lg:col-span-1 bg-white rounded-2xl border border-slate-200 shadow-sm p-4 space-y-2">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 px-2 mb-2">
            Database Tables ({tables.length})
          </div>
          <div className="space-y-1 max-h-[600px] overflow-y-auto">
            {tables.map(t => {
              const isSelected = selectedTable === t.name;
              const label = friendlyTableLabels[t.name] || t.name;
              return (
                <button
                  key={t.name}
                  onClick={() => { setSelectedTable(t.name); setSearchQuery(''); }}
                  className={`w-full text-left px-3 py-2 rounded-xl text-xs font-medium transition flex items-center justify-between ${
                    isSelected
                      ? 'bg-purple-600 text-white font-bold shadow-sm shadow-purple-600/20'
                      : 'text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  <span className="truncate pr-2">{label}</span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                    isSelected ? 'bg-purple-800 text-purple-100' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {t.row_count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Table Data View */}
        <div className="lg:col-span-3 bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
          
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-900 font-mono">{selectedTable}</h3>
                <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-xs font-bold">
                  {tableData?.total_count ?? 0} record(s)
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Primary Key: <span className="font-mono font-bold text-purple-700">{tableData?.primary_key || 'id'}</span>
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <form onSubmit={handleSearchSubmit} className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Search table..."
                  className="pl-8 pr-3 py-1.5 border border-slate-300 rounded-xl text-xs w-48 focus:ring-2 focus:ring-purple-500"
                />
              </form>

              <button
                onClick={() => {
                  setIsCreating(true);
                  setEditingRecord(null);
                  const init: Record<string, any> = {};
                  tableData?.columns.forEach(c => {
                    if (!c.pk) init[c.name] = '';
                  });
                  setNewRowData(init);
                }}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-xs font-bold transition flex items-center space-x-1 shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Record</span>
              </button>
            </div>
          </div>

          {/* Table Data Grid */}
          {loading ? (
            <div className="p-12 text-center text-xs text-slate-500 flex items-center justify-center space-x-2">
              <RefreshCw className="w-4 h-4 text-purple-600 animate-spin" />
              <span>Loading table records...</span>
            </div>
          ) : !tableData || tableData.records.length === 0 ? (
            <div className="p-12 text-center text-xs text-slate-400">
              No records found in table <span className="font-mono">{selectedTable}</span>.
            </div>
          ) : (
            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-slate-50 z-10 border-b border-slate-200">
                  <tr className="text-slate-600 font-bold">
                    <th className="py-2.5 px-3 w-16 text-center">Actions</th>
                    {tableData.columns.map(c => (
                      <th key={c.name} className="py-2.5 px-3 font-mono text-[11px] whitespace-nowrap">
                        <div className="flex items-center space-x-1">
                          <span>{c.name}</span>
                          {c.pk && <span className="text-[9px] bg-purple-100 text-purple-800 px-1 rounded font-sans">PK</span>}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tableData.records.map((row, idx) => {
                    const pkVal = row[tableData.primary_key];
                    return (
                      <tr key={idx} className="hover:bg-purple-50/30 transition">
                        <td className="py-2.5 px-3 text-center whitespace-nowrap space-x-1.5">
                          <button
                            onClick={() => handleEditClick(row)}
                            className="p-1 text-slate-500 hover:text-purple-700 hover:bg-purple-50 rounded transition"
                            title="Edit row"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteRow(String(pkVal))}
                            className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition"
                            title="Delete row"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                        {tableData.columns.map(c => {
                          const val = row[c.name];
                          const displayStr = val === null || val === undefined ? 'NULL' : typeof val === 'object' ? JSON.stringify(val) : String(val);
                          return (
                            <td key={c.name} className="py-2.5 px-3 font-mono text-[11px] max-w-xs truncate" title={displayStr}>
                              {displayStr}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

        </div>

      </div>

      {/* ── Modal: Edit Record ── */}
      {editingRecord && tableData && (
        <div className="fixed inset-0 z-60 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-2xl border border-slate-200 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2 font-bold text-sm text-slate-900">
                <Edit2 className="w-4 h-4 text-purple-600" />
                <span>Edit Record in {selectedTable}</span>
              </div>
              <button onClick={() => setEditingRecord(null)} className="p-1 text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 overflow-y-auto flex-1 p-1 text-xs">
              {tableData.columns.map(col => {
                const isPk = col.pk;
                return (
                  <div key={col.name} className="space-y-1">
                    <label className="font-bold text-slate-700 font-mono text-[11px] flex items-center justify-between">
                      <span>{col.name}</span>
                      {isPk && <span className="text-purple-600 font-sans text-[10px]">Primary Key (Immutable)</span>}
                    </label>
                    <input
                      type="text"
                      disabled={isPk}
                      value={editingRecord[col.name] ?? ''}
                      onChange={e => setEditingRecord({ ...editingRecord, [col.name]: e.target.value })}
                      className={`w-full p-2 border rounded-xl font-mono text-xs ${
                        isPk
                          ? 'bg-slate-100 border-slate-200 text-slate-500 cursor-not-allowed'
                          : 'border-slate-300 text-slate-900 focus:ring-2 focus:ring-purple-500'
                      }`}
                    />
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
              <button
                onClick={() => setEditingRecord(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={isSaving}
                className="px-5 py-2 text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 rounded-xl shadow-md transition disabled:opacity-50 flex items-center space-x-1.5"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{isSaving ? 'Saving Changes...' : 'Save & Commit to DB'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal: Add Record ── */}
      {isCreating && tableData && (
        <div className="fixed inset-0 z-60 bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full shadow-2xl border border-slate-200 space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2 font-bold text-sm text-slate-900">
                <Plus className="w-4 h-4 text-purple-600" />
                <span>Insert New Record into {selectedTable}</span>
              </div>
              <button onClick={() => setIsCreating(false)} className="p-1 text-slate-400 hover:text-slate-700">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 overflow-y-auto flex-1 p-1 text-xs">
              {tableData.columns.map(col => {
                const isPk = col.pk;
                return (
                  <div key={col.name} className="space-y-1">
                    <label className="font-bold text-slate-700 font-mono text-[11px] flex items-center justify-between">
                      <span>{col.name}</span>
                      {isPk && <span className="text-slate-400 font-sans text-[10px]">Auto-generated if left blank</span>}
                    </label>
                    <input
                      type="text"
                      placeholder={isPk ? 'Leave blank to auto-generate UUID' : `Enter ${col.name}...`}
                      value={newRowData[col.name] ?? ''}
                      onChange={e => setNewRowData({ ...newRowData, [col.name]: e.target.value })}
                      className="w-full p-2 border border-slate-300 rounded-xl font-mono text-xs text-slate-900 focus:ring-2 focus:ring-purple-500"
                    />
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
              <button
                onClick={() => setIsCreating(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateRow}
                disabled={isSaving}
                className="px-5 py-2 text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 rounded-xl shadow-md transition disabled:opacity-50 flex items-center space-x-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{isSaving ? 'Inserting...' : 'Insert Record'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
