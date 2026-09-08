'use client';

import React, { useState } from 'react';
import { User, Notification } from '../lib/types';
import { DEMO_USERS, api } from '../lib/api';
import { Bell, Sparkles, ShieldCheck, ChevronDown, CheckCircle2, AlertCircle } from 'lucide-react';

interface NavbarProps {
  currentUser: User | null;
  onUserSwitch: (email: string, password: string) => void;
  notifications: Notification[];
  onRefreshNotifications: () => void;
  onOpenCopilot?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentUser,
  onUserSwitch,
  notifications,
  onRefreshNotifications,
  onOpenCopilot,
}) => {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showNotifMenu, setShowNotifMenu] = useState(false);

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const handleNotificationClick = async (notifId: string) => {
    try {
      await api.markNotificationRead(notifId);
      onRefreshNotifications();
    } catch (err) {
      console.error(err);
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'SUPERVISOR':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'VENDOR':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'ADMIN':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Left: Branding & Core Principle */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white font-bold text-xl shadow-md shadow-blue-500/20">
            IP
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg text-slate-900 tracking-tight">Intelligent Procurement</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                v2.0
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              Deterministic Rules • Analytical Ranking • Pluggable AI
            </p>
          </div>
        </div>

        {/* Right: Role Switcher, Notifications, AI Indicator */}
        <div className="flex items-center space-x-3">
          {/* AI Status Button (Supervisor & Admin only) */}
          {(currentUser?.role === 'SUPERVISOR' || currentUser?.role === 'ADMIN') && (
            <button
              onClick={onOpenCopilot}
              className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-purple-50 hover:bg-purple-100 text-purple-800 text-xs font-semibold border border-purple-200 transition shadow-2xs cursor-pointer"
              title="Open AI Assistant"
            >
              <Sparkles className="w-3.5 h-3.5 text-purple-600 animate-pulse" />
              <span>AI Assistant: Online</span>
            </button>
          )}

          {/* Notifications Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowNotifMenu(!showNotifMenu)}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg relative transition"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-pulse">
                  {unreadCount}
                </span>
              )}
            </button>

            {showNotifMenu && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50">
                <div className="px-4 py-2 border-b border-slate-100 flex items-center justify-between">
                  <span className="font-semibold text-sm text-slate-800">Notifications ({unreadCount} unread)</span>
                  <span className="text-xs text-slate-400">Auto-synced</span>
                </div>
                <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                  {notifications.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-400">No notifications yet</div>
                  ) : (
                    notifications.map(notif => (
                      <div
                        key={notif.id}
                        onClick={() => handleNotificationClick(notif.id)}
                        className={`p-3 text-xs cursor-pointer hover:bg-slate-50 transition ${notif.is_read ? 'opacity-60' : 'bg-blue-50/40 font-medium'}`}
                      >
                        <div className="flex items-start justify-between">
                          <span className="text-slate-900 font-semibold">{notif.title}</span>
                          <span className="text-[10px] text-slate-400">{new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <p className="text-slate-600 mt-1">{notif.message}</p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User & Role Switcher */}
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center space-x-2 pl-2 pr-3 py-1.5 rounded-lg border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition text-left"
            >
              <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs">
                {currentUser ? currentUser.name.charAt(0) : '?'}
              </div>
              <div className="hidden sm:block text-xs leading-tight">
                <div className="font-semibold text-slate-800">{currentUser?.name || 'Switch Role'}</div>
                <div className="flex items-center space-x-1 mt-0.5">
                  <span className={`inline-block px-1.5 py-0.2 rounded border text-[10px] font-bold uppercase ${getRoleBadgeColor(currentUser?.role || '')}`}>
                    {currentUser?.role || 'Select'}
                  </span>
                  {currentUser?.department_name && (
                    <span className="text-slate-400 text-[10px]">• {currentUser.department_name}</span>
                  )}
                </div>
              </div>
              <ChevronDown className="w-4 h-4 text-slate-400" />
            </button>

            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-2xl border border-slate-200 py-2 z-50">
                <div className="px-3 py-2 border-b border-slate-100">
                  <div className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                    Instant Demo Persona Switcher
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Switch roles instantly to test all multi-actor workflows.
                  </p>
                </div>
                <div className="py-1 max-h-72 overflow-y-auto">
                  {DEMO_USERS.map((u, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        onUserSwitch(u.email, u.password);
                        setShowUserMenu(false);
                      }}
                      className={`w-full px-3 py-2 text-left text-xs hover:bg-slate-100 flex items-center justify-between transition ${currentUser?.email === u.email ? 'bg-blue-50/80 font-bold text-blue-700' : 'text-slate-700'}`}
                    >
                      <div>
                        <div>{u.label}</div>
                        <div className="text-[10px] text-slate-400">{u.email}</div>
                      </div>
                      <span className={`px-1.5 py-0.5 rounded border text-[9px] font-bold ${getRoleBadgeColor(u.role)}`}>
                        {u.role}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
