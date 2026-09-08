'use client';

import React from 'react';
import { Role } from '../lib/types';
import {
  LayoutDashboard,
  FileSpreadsheet,
  Send,
  CheckSquare,
  FileCheck2,
  BrainCircuit,
  Building2,
  BookOpen,
  Database
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  role: Role;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab, role }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard Overview', icon: LayoutDashboard, roles: ['EMPLOYEE', 'SUPERVISOR', 'VENDOR', 'ADMIN'] },
    { id: 'requests', label: 'Purchase Requests', icon: FileSpreadsheet, roles: ['EMPLOYEE', 'SUPERVISOR', 'ADMIN'] },
    { id: 'rfqs', label: 'RFQ & Quotations', icon: Send, roles: ['SUPERVISOR', 'VENDOR', 'ADMIN'] },
    { id: 'orders', label: 'Purchase Orders', icon: FileCheck2, roles: ['EMPLOYEE', 'SUPERVISOR', 'VENDOR', 'ADMIN'] },
    { id: 'ai', label: 'AI Assistant', icon: BrainCircuit, roles: ['SUPERVISOR', 'ADMIN'] },
  ];

  const visibleItems = navItems.filter(item => item.roles.includes(role));

  return (
    <aside className="w-64 bg-white border-r border-slate-200 min-h-[calc(100vh-4rem)] p-4 flex flex-col justify-between shrink-0">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Main Navigation
        </div>
        {visibleItems.map(item => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition ${
                isActive
                  ? 'bg-blue-50 text-blue-700 font-semibold shadow-sm border border-blue-100'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* System Integrity Footer */}
      <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-xs text-slate-500 space-y-1">
        <div className="font-semibold text-slate-700 flex items-center space-x-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>Dual Architecture Active</span>
        </div>
        <p className="text-[11px] leading-relaxed text-slate-400">
          Core procurement transactions remain 100% operational with or without AI providers.
        </p>
      </div>
    </aside>
  );
};
