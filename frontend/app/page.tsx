'use client';

import React, { useState, useEffect } from 'react';
import { User, PurchaseRequest, Item, RFQ, PurchaseOrder, Notification, QuotationAnalysis } from '../lib/types';
import { api, DEMO_USERS } from '../lib/api';
import { subscribeSyncEvent } from '../lib/sync';
import { Navbar } from '../components/Navbar';
import { Sidebar } from '../components/Sidebar';
import { CreatePRModal } from '../components/CreatePRModal';
import { CheckingSheet } from '../components/CheckingSheet';
import { QuotationComparison } from '../components/QuotationComparison';
import { VendorPortal } from '../components/VendorPortal';
import { AICopilotDrawer } from '../components/AICopilotDrawer';
import RevisePRModal from '../components/RevisePRModal';
import { SubmitQuotationModal } from '../components/SubmitQuotationModal';
import { getWorkflowState, categorizePRForRole, getPrimaryAction } from '../lib/workflow';
import {
  FilePlus,
  FileSpreadsheet,
  FileCheck2,
  Clock,
  Send,
  Sparkles,
  Download,
  AlertCircle,
  CheckCircle2,
  BookOpen,
  ArrowUpRight,
  ShieldCheck,
  Search,
  Trash2,
  RotateCcw,
  Zap,
  History,
  Layers,
  ArrowRight,
  AlertTriangle,
  Check,
  Eye,
  DollarSign,
  Calendar
} from 'lucide-react';

export default function Home() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [loading, setLoading] = useState<boolean>(true);

  // Core Data Collections
  const [prs, setPrs] = useState<PurchaseRequest[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [orders, setOrders] = useState<PurchaseOrder[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  // Modals & Panels
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [selectedPrDetail, setSelectedPrDetail] = useState<PurchaseRequest | null>(null);
  const [showCheckingSheet, setShowCheckingSheet] = useState<boolean>(false);
  const [showReviseModal, setShowReviseModal] = useState<boolean>(false);
  const [selectedPrForRevise, setSelectedPrForRevise] = useState<PurchaseRequest | null>(null);
  const [selectedPrForQuotes, setSelectedPrForQuotes] = useState<PurchaseRequest | null>(null);
  const [selectedRfqForQuote, setSelectedRfqForQuote] = useState<RFQ | null>(null);
  const [showQuoteModal, setShowQuoteModal] = useState<boolean>(false);
  const [quotationAnalysis, setQuotationAnalysis] = useState<QuotationAnalysis | null>(null);
  const [showCopilot, setShowCopilot] = useState<boolean>(false);

  // Queue segment filter states
  const [dashboardQueueFilter, setDashboardQueueFilter] = useState<'ACTION_REQUIRED' | 'WAITING' | 'HISTORY' | 'ALL'>('ALL');
  const [requestsQueueFilter, setRequestsQueueFilter] = useState<'ALL' | 'ACTION_REQUIRED' | 'WAITING' | 'HISTORY'>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const handleTabChange = (tab: string) => {
    setCurrentTab(tab);
    if (typeof window !== 'undefined') {
      localStorage.setItem('ipms_active_tab', tab);
    }
  };

  // Initial Auth Login with Role & Tab Persistence
  useEffect(() => {
    const initAuth = async () => {
      try {
        let savedEmail = typeof window !== 'undefined' ? localStorage.getItem('ipms_active_user_email') : null;
        let targetUser = DEMO_USERS.find(u => u.email === savedEmail) || DEMO_USERS[0];

        const savedTab = typeof window !== 'undefined' ? localStorage.getItem('ipms_active_tab') : null;
        if (savedTab) {
          setCurrentTab(savedTab);
        }

        const authData = await api.login(targetUser.email, targetUser.password);
        setCurrentUser(authData.user);
        if (typeof window !== 'undefined') {
          localStorage.setItem('ipms_active_user_email', targetUser.email);
        }
      } catch (err) {
        console.error('Initial login failed:', err);
      } finally {
        setLoading(false);
      }
    };
    initAuth();
  }, []);

  // Fetch all domain data whenever currentUser changes
  const refreshAllData = async () => {
    if (!currentUser) return;
    try {
      const [prsRes, itemsRes, rfqsRes, posRes, notifsRes] = await Promise.all([
        api.getPRs(),
        api.getItems(),
        api.getRFQs(),
        api.getPOs(),
        api.getNotifications(),
      ]);
      setPrs(prsRes);
      setItems(itemsRes);
      setRfqs(rfqsRes);
      setOrders(posRes);
      setNotifications(notifsRes);

      if (selectedPrForQuotes) {
        try {
          const qa = await api.getQuotationAnalysis(selectedPrForQuotes.id);
          if (qa && qa.purchase_request_id === selectedPrForQuotes.id) {
            setQuotationAnalysis(qa);
          } else {
            setQuotationAnalysis(null);
          }
        } catch {
          setQuotationAnalysis(null);
        }
      }
    } catch (err) {
      console.error('Data refresh failed:', err);
    }
  };

  useEffect(() => {
    refreshAllData();
  }, [currentUser]);

  // Real-time cross-tab synchronization listener
  useEffect(() => {
    const unsubscribe = subscribeSyncEvent(async (payload) => {
      if (!currentUser) return;
      try {
        const [prsRes, itemsRes, rfqsRes, posRes, notifsRes] = await Promise.all([
          api.getPRs(),
          api.getItems(),
          api.getRFQs(),
          api.getPOs(),
          api.getNotifications(),
        ]);
        setPrs(prsRes);
        setItems(itemsRes);
        setRfqs(rfqsRes);
        setOrders(posRes);
        setNotifications(notifsRes);

        // If checking sheet modal is open, refresh its data in place
        if (selectedPrDetail) {
          try {
            const updatedDetail = await api.getPRDetail(selectedPrDetail.id);
            setSelectedPrDetail(updatedDetail);
          } catch (_) {}
        }

        // If quotation comparison is open, refresh analysis
        if (selectedPrForQuotes) {
          try {
            const qa = await api.getQuotationAnalysis(selectedPrForQuotes.id);
            if (qa && qa.purchase_request_id === selectedPrForQuotes.id) {
              setQuotationAnalysis(qa);
            }
          } catch (_) {}
        }
      } catch (err) {
        console.error('Real-time sync refresh error:', err);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [currentUser, selectedPrDetail?.id, selectedPrForQuotes?.id]);

  const handleUserSwitch = async (email: string) => {
    const targetUser = DEMO_USERS.find(u => u.email === email);
    if (!targetUser) return;
    setLoading(true);
    try {
      const authData = await api.login(targetUser.email, targetUser.password);
      setCurrentUser(authData.user);
      if (typeof window !== 'undefined') {
        localStorage.setItem('ipms_active_user_email', targetUser.email);
      }
      const [prsRes, itemsRes, rfqsRes, posRes, notifsRes] = await Promise.all([
        api.getPRs(),
        api.getItems(),
        api.getRFQs(),
        api.getPOs(),
        api.getNotifications(),
      ]);
      setPrs(prsRes);
      setItems(itemsRes);
      setRfqs(rfqsRes);
      setOrders(posRes);
      setNotifications(notifsRes);
      // Reset active modals
      setShowCheckingSheet(false);
      setShowReviseModal(false);
      setSelectedPrForQuotes(null);
    } catch (err) {
      console.error('Switch failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCheckingSheet = async (prId: string) => {
    try {
      const detail = await api.getPRDetail(prId);
      setSelectedPrDetail(detail);
      setShowCheckingSheet(true);
    } catch (err) {
      console.error(err);
    }
  };

  const handleOpenQuotationComparison = async (pr: PurchaseRequest) => {
    setSelectedPrForQuotes(pr);
    setQuotationAnalysis(null);
    handleTabChange('rfqs');
    try {
      const qa = await api.getQuotationAnalysis(pr.id);
      if (qa && qa.purchase_request_id === pr.id) {
        setQuotationAnalysis(qa);
      } else {
        setQuotationAnalysis(null);
      }
    } catch (err) {
      console.error(err);
      setQuotationAnalysis(null);
    }
  };

  const handleOpenReviseModal = (pr: PurchaseRequest) => {
    setSelectedPrForRevise(pr);
    setShowReviseModal(true);
  };

  const handleDeletePR = async (prId: string, refNum: string) => {
    if (!confirm(`Are you sure you want to permanently delete purchase request ${refNum}?`)) {
      return;
    }
    try {
      await api.deletePR(prId);
      await refreshAllData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete request.');
    }
  };

  if (loading && !currentUser) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-600 font-medium">
        <div className="flex items-center space-x-3">
          <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading Intelligent Procurement System...</span>
        </div>
      </div>
    );
  }

  const role = currentUser?.role || 'EMPLOYEE';

  // Role-based categorized queues
  const actionRequiredPRs = prs.filter(p => categorizePRForRole(p, role) === 'ACTION_REQUIRED');
  const waitingPRs = prs.filter(p => categorizePRForRole(p, role) === 'WAITING');
  const historyPRs = prs.filter(p => categorizePRForRole(p, role) === 'HISTORY');

  // Vendor-specific calculation helpers
  const isRfqExpired = (rfq: RFQ) => {
    if (rfq.status === 'RFQ_EXPIRED') return true;
    if (rfq.due_at && !rfq.has_quotation && new Date(rfq.due_at) < new Date()) return true;
    return false;
  };

  const vendorPendingRFQs = rfqs.filter(r => !r.has_quotation && !isRfqExpired(r));
  const vendorSubmittedRFQs = rfqs.filter(r => r.has_quotation);
  const vendorExpiredRFQs = rfqs.filter(r => !r.has_quotation && isRfqExpired(r));
  const vendorOrders = orders;
  const vendorTotalRevenue = vendorOrders.reduce((sum, o) => sum + (o.approved_amount || 0), 0);

  const getVendorDashboardItems = () => {
    const rfqItems = rfqs.map(r => ({
      id: r.id,
      itemType: 'RFQ' as const,
      ref: r.reference_number,
      pr_ref: r.pr_reference,
      item_name: r.item_name,
      quantity: r.quantity,
      item_unit: r.item_unit,
      date: r.due_at || r.issued_at,
      isExpired: isRfqExpired(r),
      hasQuotation: r.has_quotation,
      amount: null as number | null,
      status: r.has_quotation ? 'QUOTED' : isRfqExpired(r) ? 'EXPIRED' : 'ACTION_REQUIRED',
      rawRfq: r,
      rawPo: null as PurchaseOrder | null,
    }));

    const orderItems = orders.map(o => ({
      id: o.id,
      itemType: 'PO' as const,
      ref: o.po_number,
      pr_ref: o.pr_reference,
      item_name: o.item_name,
      quantity: o.quantity,
      item_unit: o.item_unit,
      date: o.generated_at,
      isExpired: false,
      hasQuotation: true,
      amount: o.approved_amount,
      status: 'PO_AWARDED',
      rawRfq: null as RFQ | null,
      rawPo: o,
    }));

    let combined = [...rfqItems, ...orderItems];

    if (dashboardQueueFilter === 'ACTION_REQUIRED') {
      combined = combined.filter(i => i.status === 'ACTION_REQUIRED');
    } else if (dashboardQueueFilter === 'WAITING') {
      combined = combined.filter(i => i.status === 'QUOTED');
    } else if (dashboardQueueFilter === 'HISTORY') {
      combined = combined.filter(i => i.status === 'PO_AWARDED' || i.status === 'EXPIRED');
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      combined = combined.filter(
        i =>
          i.ref.toLowerCase().includes(q) ||
          i.pr_ref.toLowerCase().includes(q) ||
          i.item_name.toLowerCase().includes(q) ||
          i.status.toLowerCase().includes(q)
      );
    }

    return combined;
  };

  // Filtered PR list for Dashboard table
  const getDashboardPRs = () => {
    let list = prs;
    if (dashboardQueueFilter === 'ACTION_REQUIRED') list = actionRequiredPRs;
    else if (dashboardQueueFilter === 'WAITING') list = waitingPRs;
    else if (dashboardQueueFilter === 'HISTORY') list = historyPRs;
    return list.slice(0, 6);
  };

  // Filtered PR list for Requests tab table
  const getRequestsPRs = () => {
    let list = prs;
    if (requestsQueueFilter === 'ACTION_REQUIRED') list = actionRequiredPRs;
    else if (requestsQueueFilter === 'WAITING') list = waitingPRs;
    else if (requestsQueueFilter === 'HISTORY') list = historyPRs;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(
        p =>
          p.reference_number.toLowerCase().includes(q) ||
          (p.item_name && p.item_name.toLowerCase().includes(q)) ||
          (p.department_name && p.department_name.toLowerCase().includes(q)) ||
          (p.selected_vendor_name && p.selected_vendor_name.toLowerCase().includes(q)) ||
          p.status.toLowerCase().includes(q)
      );
    }
    return list;
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      {/* Top Navbar */}
      <Navbar
        currentUser={currentUser}
        onUserSwitch={handleUserSwitch}
        notifications={notifications}
        onRefreshNotifications={refreshAllData}
        onOpenCopilot={() => setShowCopilot(true)}
      />

      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        {/* Role-based Sidebar */}
        <Sidebar currentTab={currentTab} onSelectTab={handleTabChange} role={role} />

        {/* Main Content Area */}
        <main className="flex-1 p-6 space-y-6 overflow-y-auto">
          
          {/* TAB 1: DASHBOARD OVERVIEW */}
          {currentTab === 'dashboard' && (
            role === 'VENDOR' ? (
              /* VENDOR DEDICATED DASHBOARD */
              <div className="space-y-6">
                {/* Vendor Welcome Banner */}
                <div className="p-6 bg-gradient-to-r from-amber-600 via-amber-700 to-orange-800 rounded-3xl text-white shadow-lg shadow-amber-900/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div>
                    <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-500/30 border border-amber-400/30 text-xs font-semibold mb-2">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Direct Supplier Portal • RFQ Bidding & Purchase Orders</span>
                    </div>
                    <h1 className="text-2xl font-black tracking-tight">
                      Welcome, {currentUser?.name}
                    </h1>
                    <p className="text-amber-100 text-xs max-w-xl mt-1 leading-relaxed">
                      Active supplier account: <span className="font-bold text-white">{currentUser?.name}</span> ({currentUser?.email}).
                      Review invited RFQs, commit competitive delivery dates, and track awarded purchase orders.
                    </p>
                  </div>

                  <button
                    onClick={() => handleTabChange('rfqs')}
                    className="px-5 py-3 rounded-2xl bg-white text-amber-900 hover:bg-amber-50 font-bold text-xs shadow-xl transition flex items-center space-x-2 shrink-0"
                  >
                    <Send className="w-4 h-4 text-amber-600" />
                    <span>View All RFQs ({rfqs.length})</span>
                  </button>
                </div>

                {/* Vendor KPI Metric Cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Card 1: Action Required (Pending Quotations) */}
                  <button
                    onClick={() => setDashboardQueueFilter('ACTION_REQUIRED')}
                    className={`p-4 rounded-2xl border text-left transition-all ${
                      dashboardQueueFilter === 'ACTION_REQUIRED'
                        ? 'bg-amber-50/80 border-amber-300 ring-2 ring-amber-400 shadow-md'
                        : 'bg-white border-slate-200/80 shadow-sm hover:border-amber-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-[11px] font-bold text-amber-700 uppercase tracking-wider flex items-center space-x-1">
                        <Zap className="w-3.5 h-3.5 text-amber-600" />
                        <span>Action Required</span>
                      </div>
                      {vendorPendingRFQs.length > 0 && (
                        <span className="px-1.5 py-0.5 bg-amber-500 text-white font-bold text-[10px] rounded-full animate-pulse">
                          {vendorPendingRFQs.length}
                        </span>
                      )}
                    </div>
                    <div className="text-2xl font-black text-slate-900 mt-1">{vendorPendingRFQs.length}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      RFQs awaiting your quotation
                    </div>
                  </button>

                  {/* Card 2: Submitted Proposals */}
                  <button
                    onClick={() => setDashboardQueueFilter('WAITING')}
                    className={`p-4 rounded-2xl border text-left transition-all ${
                      dashboardQueueFilter === 'WAITING'
                        ? 'bg-blue-50/80 border-blue-300 ring-2 ring-blue-400 shadow-md'
                        : 'bg-white border-slate-200/80 shadow-sm hover:border-blue-300'
                    }`}
                  >
                    <div className="text-[11px] font-bold text-blue-700 uppercase tracking-wider flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5 text-blue-600" />
                      <span>Submitted Quotes</span>
                    </div>
                    <div className="text-2xl font-black text-slate-900 mt-1">{vendorSubmittedRFQs.length}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      Proposals under evaluation
                    </div>
                  </button>

                  {/* Card 3: Awarded POs */}
                  <button
                    onClick={() => setDashboardQueueFilter('HISTORY')}
                    className={`p-4 rounded-2xl border text-left transition-all ${
                      dashboardQueueFilter === 'HISTORY'
                        ? 'bg-emerald-50/80 border-emerald-300 ring-2 ring-emerald-400 shadow-md'
                        : 'bg-white border-slate-200/80 shadow-sm hover:border-emerald-300'
                    }`}
                  >
                    <div className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider flex items-center space-x-1">
                      <FileCheck2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Awarded Orders</span>
                    </div>
                    <div className="text-2xl font-black text-slate-900 mt-1">{vendorOrders.length}</div>
                    <div className="text-[11px] text-emerald-600 font-semibold mt-0.5">
                      Official Purchase Orders won
                    </div>
                  </button>

                  {/* Card 4: Total Contract Value */}
                  <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-sm space-y-1">
                    <div className="text-[11px] font-bold text-purple-700 uppercase tracking-wider flex items-center space-x-1">
                      <DollarSign className="w-3.5 h-3.5 text-purple-600" />
                      <span>Total Contract Value</span>
                    </div>
                    <div className="text-2xl font-black text-slate-900">${vendorTotalRevenue.toLocaleString()}</div>
                    <div className="text-[11px] text-slate-500">
                      Approved fulfillment revenue
                    </div>
                  </div>
                </div>

                {/* Vendor Action Required Hero Alert */}
                {vendorPendingRFQs.length > 0 && (
                  <div className="p-5 bg-gradient-to-r from-amber-500/10 via-amber-50 to-orange-50 rounded-2xl border border-amber-300/80 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2 text-amber-900 font-bold text-sm">
                        <Zap className="w-4 h-4 text-amber-600" />
                        <span>Action Required: {vendorPendingRFQs.length} RFQ(s) Awaiting Your Quotation</span>
                      </div>
                      <span className="text-xs text-amber-700 font-medium">
                        High Priority Bidding
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {vendorPendingRFQs.map(rfq => (
                        <div key={rfq.id} className="p-3.5 bg-white rounded-xl border border-amber-200/80 shadow-sm flex items-center justify-between space-x-3">
                          <div className="space-y-1 min-w-0 flex-1">
                            <div className="flex items-center space-x-2">
                              <span className="font-bold text-xs text-slate-900">{rfq.reference_number}</span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold border bg-amber-100 text-amber-800 border-amber-200">
                                Quote Required
                              </span>
                            </div>
                            <div className="text-xs text-slate-600 truncate">
                              <span className="font-semibold text-slate-800">{rfq.item_name}</span> ({rfq.quantity} {rfq.item_unit})
                            </div>
                            <div className="text-[11px] text-slate-500 flex items-center space-x-1">
                              <Clock className="w-3 h-3 text-slate-400" />
                              <span>{rfq.due_at ? `Due: ${new Date(rfq.due_at).toLocaleDateString()}` : 'Immediate'}</span>
                            </div>
                          </div>

                          <button
                            onClick={() => {
                              setSelectedRfqForQuote(rfq);
                              setShowQuoteModal(true);
                            }}
                            className="px-3.5 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 shrink-0 bg-blue-600 hover:bg-blue-700 text-white shadow-sm"
                          >
                            <Send className="w-3.5 h-3.5" />
                            <span>Submit Quote</span>
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Vendor Unified Bidding & Orders Table */}
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">Supplier RFQ & Order Pipeline</h3>
                      <p className="text-xs text-slate-500">Real-time status of commercial bids, proposals, and awarded contracts</p>
                    </div>
                    
                    {/* Queue Segment Selector */}
                    <div className="flex items-center p-1 bg-slate-100 rounded-xl space-x-1 text-xs font-bold text-slate-600 self-start sm:self-auto">
                      <button
                        onClick={() => setDashboardQueueFilter('ALL')}
                        className={`px-3 py-1.5 rounded-lg transition ${
                          dashboardQueueFilter === 'ALL'
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'hover:text-slate-900'
                        }`}
                      >
                        All ({rfqs.length + vendorOrders.length})
                      </button>
                      <button
                        onClick={() => setDashboardQueueFilter('ACTION_REQUIRED')}
                        className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                          dashboardQueueFilter === 'ACTION_REQUIRED'
                            ? 'bg-amber-500 text-white shadow-sm'
                            : 'hover:text-amber-700'
                        }`}
                      >
                        <Zap className="w-3 h-3" />
                        <span>Pending Quotes ({vendorPendingRFQs.length})</span>
                      </button>
                      <button
                        onClick={() => setDashboardQueueFilter('WAITING')}
                        className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                          dashboardQueueFilter === 'WAITING'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'hover:text-blue-700'
                        }`}
                      >
                        <Clock className="w-3 h-3" />
                        <span>Submitted ({vendorSubmittedRFQs.length})</span>
                      </button>
                      <button
                        onClick={() => setDashboardQueueFilter('HISTORY')}
                        className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                          dashboardQueueFilter === 'HISTORY'
                            ? 'bg-emerald-600 text-white shadow-sm'
                            : 'hover:text-emerald-700'
                        }`}
                      >
                        <FileCheck2 className="w-3 h-3" />
                        <span>Awarded POs ({vendorOrders.length})</span>
                      </button>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                          <th className="py-2.5 px-3">Reference / Type</th>
                          <th className="py-2.5 px-3">Item & Quantity</th>
                          <th className="py-2.5 px-3">Status</th>
                          <th className="py-2.5 px-3">Timeline / Due Date</th>
                          <th className="py-2.5 px-3">Commercial Amount</th>
                          <th className="py-2.5 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {getVendorDashboardItems().length === 0 ? (
                          <tr>
                            <td colSpan={6} className="py-8 text-center text-slate-400 font-medium">
                              No records found in this category.
                            </td>
                          </tr>
                        ) : (
                          getVendorDashboardItems().map(item => (
                            <tr key={item.id} className={`hover:bg-slate-50 transition ${item.status === 'ACTION_REQUIRED' ? 'bg-amber-50/20' : ''}`}>
                              <td className="py-3 px-3">
                                <div className="flex items-center space-x-1.5">
                                  <span className="font-bold text-slate-900">{item.ref}</span>
                                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                                    item.itemType === 'PO' ? 'bg-purple-100 text-purple-800 border border-purple-200' : 'bg-blue-100 text-blue-800 border border-blue-200'
                                  }`}>
                                    {item.itemType}
                                  </span>
                                </div>
                                <span className="text-[10px] text-slate-400 block">Ref PR: {item.pr_ref}</span>
                              </td>
                              <td className="py-3 px-3">
                                <span className="font-semibold text-slate-800 block">{item.item_name}</span>
                                <span className="text-slate-400 text-[10px]">{item.quantity} {item.item_unit}</span>
                              </td>
                              <td className="py-3 px-3">
                                {item.status === 'ACTION_REQUIRED' && (
                                  <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold border bg-amber-100 text-amber-800 border-amber-200 inline-flex items-center space-x-1">
                                    <Zap className="w-3 h-3 text-amber-600" />
                                    <span>Action Required</span>
                                  </span>
                                )}
                                {item.status === 'QUOTED' && (
                                  <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold border bg-blue-100 text-blue-800 border-blue-200 inline-flex items-center space-x-1">
                                    <CheckCircle2 className="w-3 h-3 text-blue-600" />
                                    <span>Quote Submitted</span>
                                  </span>
                                )}
                                {item.status === 'PO_AWARDED' && (
                                  <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold border bg-emerald-100 text-emerald-800 border-emerald-200 inline-flex items-center space-x-1">
                                    <Check className="w-3 h-3 text-emerald-600" />
                                    <span>PO Awarded</span>
                                  </span>
                                )}
                                {item.status === 'EXPIRED' && (
                                  <span className="px-2.5 py-1 rounded-lg text-[10px] font-bold border bg-rose-100 text-rose-800 border-rose-200">
                                    Expired
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-3 text-slate-600">
                                {item.date ? new Date(item.date).toLocaleDateString() : '-'}
                              </td>
                              <td className="py-3 px-3 font-bold text-slate-900">
                                {item.amount ? `$${item.amount.toLocaleString()}` : '-'}
                              </td>
                              <td className="py-3 px-3 text-right space-x-2">
                                {item.status === 'ACTION_REQUIRED' && item.rawRfq && (
                                  <button
                                    onClick={() => {
                                      setSelectedRfqForQuote(item.rawRfq);
                                      setShowQuoteModal(true);
                                    }}
                                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition inline-flex items-center space-x-1 shadow-sm"
                                  >
                                    <Send className="w-3 h-3" />
                                    <span>Submit Quote</span>
                                  </button>
                                )}
                                {item.status === 'QUOTED' && (
                                  <span className="text-[11px] text-slate-400 font-medium">Under Evaluation</span>
                                )}
                                {item.itemType === 'PO' && item.rawPo && (
                                  <button
                                    onClick={() => api.downloadPO(item.rawPo!.id, item.rawPo!.po_number)}
                                    className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 rounded-lg text-xs font-bold transition inline-flex items-center space-x-1.5"
                                  >
                                    <Download className="w-3.5 h-3.5" />
                                    <span>Download PO</span>
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              /* EMPLOYEE & SUPERVISOR DASHBOARD */
              <div className="space-y-6">
                
                {/* Welcome & Primary CTA Banner */}
                <div className="p-6 bg-gradient-to-r from-blue-700 via-blue-800 to-indigo-900 rounded-3xl text-white shadow-lg shadow-blue-900/10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div>
                    <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-500/30 border border-blue-400/30 text-xs font-semibold mb-2">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Deterministic + Analytical + Pluggable AI</span>
                    </div>
                    <h1 className="text-2xl font-black tracking-tight">
                      Welcome, {currentUser?.name}
                    </h1>
                    <p className="text-blue-100 text-xs max-w-xl mt-1 leading-relaxed">
                      Active role: <span className="font-bold text-white uppercase">{role}</span>
                      {currentUser?.department_name && ` • ${currentUser.department_name}`}.
                      Procurement workflows are strictly verified, multi-factor scored, and human-authorized.
                    </p>
                  </div>

                  {(role === 'EMPLOYEE' || role === 'ADMIN') && (
                    <button
                      onClick={() => setShowCreateModal(true)}
                      className="px-5 py-3 rounded-2xl bg-white text-blue-900 hover:bg-blue-50 font-bold text-xs shadow-xl transition flex items-center space-x-2 shrink-0"
                    >
                      <FilePlus className="w-4 h-4 text-blue-600" />
                      <span>Create Purchase Request</span>
                    </button>
                  )}
                </div>

                {/* KPI Metric Cards (Accurately partitioned by role action ownership) */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  
                  {/* Card 1: Action Required (Active Queue) */}
                  <button
                    onClick={() => {
                      setDashboardQueueFilter('ACTION_REQUIRED');
                    }}
                    className={`p-4 rounded-2xl border text-left transition-all ${
                      dashboardQueueFilter === 'ACTION_REQUIRED'
                        ? 'bg-amber-50/80 border-amber-300 ring-2 ring-amber-400 shadow-md'
                        : 'bg-white border-slate-200/80 shadow-sm hover:border-amber-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-[11px] font-bold text-amber-700 uppercase tracking-wider flex items-center space-x-1">
                        <Zap className="w-3.5 h-3.5 text-amber-600" />
                        <span>Action Required</span>
                      </div>
                      {actionRequiredPRs.length > 0 && (
                        <span className="px-1.5 py-0.5 bg-amber-500 text-white font-bold text-[10px] rounded-full animate-pulse">
                          {actionRequiredPRs.length}
                        </span>
                      )}
                    </div>
                    <div className="text-2xl font-black text-slate-900 mt-1">{actionRequiredPRs.length}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {role === 'EMPLOYEE' ? 'Revisions waiting for you' : 'Tasks requiring your action'}
                    </div>
                  </button>

                  {/* Card 2: In Progress / Waiting on Others */}
                  <button
                    onClick={() => {
                      setDashboardQueueFilter('WAITING');
                    }}
                    className={`p-4 rounded-2xl border text-left transition-all ${
                      dashboardQueueFilter === 'WAITING'
                        ? 'bg-blue-50/80 border-blue-300 ring-2 ring-blue-400 shadow-md'
                        : 'bg-white border-slate-200/80 shadow-sm hover:border-blue-300'
                    }`}
                  >
                    <div className="text-[11px] font-bold text-blue-700 uppercase tracking-wider flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5 text-blue-600" />
                      <span>In Progress</span>
                    </div>
                    <div className="text-2xl font-black text-slate-900 mt-1">{waitingPRs.length}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      {role === 'EMPLOYEE' ? 'Awaiting supervisor/RFQs' : 'Awaiting employee/vendors'}
                    </div>
                  </button>

                  {/* Card 3: Completed / History */}
                  <button
                    onClick={() => {
                      setDashboardQueueFilter('HISTORY');
                    }}
                    className={`p-4 rounded-2xl border text-left transition-all ${
                      dashboardQueueFilter === 'HISTORY'
                        ? 'bg-emerald-50/80 border-emerald-300 ring-2 ring-emerald-400 shadow-md'
                        : 'bg-white border-slate-200/80 shadow-sm hover:border-emerald-300'
                    }`}
                  >
                    <div className="text-[11px] font-bold text-emerald-700 uppercase tracking-wider flex items-center space-x-1">
                      <History className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Completed / History</span>
                    </div>
                    <div className="text-2xl font-black text-slate-900 mt-1">{historyPRs.length}</div>
                    <div className="text-[11px] text-emerald-600 font-semibold mt-0.5">
                      POs generated & rejected
                    </div>
                  </button>

                  {/* Card 4: Official Purchase Orders */}
                  <div className="p-4 bg-white rounded-2xl border border-slate-200/80 shadow-sm space-y-1">
                    <div className="text-[11px] font-bold text-purple-700 uppercase tracking-wider flex items-center space-x-1">
                      <FileCheck2 className="w-3.5 h-3.5 text-purple-600" />
                      <span>Purchase Orders</span>
                    </div>
                    <div className="text-2xl font-black text-slate-900">{orders.length}</div>
                    <div className="text-[11px] text-slate-500">
                      <span>Authorized PO documents</span>
                    </div>
                  </div>

                </div>

                {/* Action Required Hero Alert (Renders when current user has immediate actionable items) */}
                {actionRequiredPRs.length > 0 && (
                  <div className="p-5 bg-gradient-to-r from-amber-500/10 via-amber-50 to-orange-50 rounded-2xl border border-amber-300/80 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2 text-amber-900 font-bold text-sm">
                        <Zap className="w-4 h-4 text-amber-600" />
                        <span>Action Required from You ({actionRequiredPRs.length} {actionRequiredPRs.length === 1 ? 'item' : 'items'})</span>
                      </div>
                      <span className="text-xs text-amber-700 font-medium">
                        High Priority Queue
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {actionRequiredPRs.map(pr => {
                        const act = getPrimaryAction(pr, role);
                        const stateInfo = getWorkflowState(pr.status);
                        return (
                          <div key={pr.id} className="p-3.5 bg-white rounded-xl border border-amber-200/80 shadow-sm flex items-center justify-between space-x-3">
                            <div className="space-y-1 min-w-0 flex-1">
                              <div className="flex items-center space-x-2">
                                <span className="font-bold text-xs text-slate-900">{pr.reference_number}</span>
                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${stateInfo.badgeStyle}`}>
                                  {stateInfo.label}
                                </span>
                              </div>
                              <div className="text-xs text-slate-600 truncate">
                                <span className="font-semibold text-slate-800">{pr.item_name}</span> ({pr.quantity} {pr.item_unit})
                              </div>
                              {pr.status === 'REVISION_REQUIRED' && pr.reviews && pr.reviews.length > 0 && (
                                <p className="text-[11px] text-amber-900 bg-amber-50 p-1.5 rounded border border-amber-200/60 line-clamp-1 italic">
                                  &ldquo;{pr.reviews[pr.reviews.length - 1].reason}&rdquo;
                                </p>
                              )}
                            </div>

                            <button
                              onClick={() => {
                                if (act.type === 'REVISE') handleOpenReviseModal(pr);
                                else if (act.type === 'EVALUATE') handleOpenQuotationComparison(pr);
                                else handleOpenCheckingSheet(pr.id);
                              }}
                              className={`px-3.5 py-2 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 shrink-0 ${act.style}`}
                            >
                              <span>{act.label}</span>
                              <ArrowRight className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Segmented Procurement Requests Table */}
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                    <div>
                      <h3 className="text-base font-bold text-slate-900">Procurement Workflow Queues</h3>
                      <p className="text-xs text-slate-500">Separated by action ownership: Action Required vs Waiting vs History</p>
                    </div>
                    
                    {/* Queue Segment Selector */}
                    <div className="flex items-center p-1 bg-slate-100 rounded-xl space-x-1 text-xs font-bold text-slate-600 self-start sm:self-auto">
                      <button
                        onClick={() => setDashboardQueueFilter('ALL')}
                        className={`px-3 py-1.5 rounded-lg transition ${
                          dashboardQueueFilter === 'ALL'
                            ? 'bg-white text-slate-900 shadow-sm'
                            : 'hover:text-slate-900'
                        }`}
                      >
                        All ({prs.length})
                      </button>
                      <button
                        onClick={() => setDashboardQueueFilter('ACTION_REQUIRED')}
                        className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                          dashboardQueueFilter === 'ACTION_REQUIRED'
                            ? 'bg-amber-500 text-white shadow-sm'
                            : 'hover:text-amber-700'
                        }`}
                      >
                        <Zap className="w-3 h-3" />
                        <span>Action Required ({actionRequiredPRs.length})</span>
                      </button>
                      <button
                        onClick={() => setDashboardQueueFilter('WAITING')}
                        className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                          dashboardQueueFilter === 'WAITING'
                            ? 'bg-blue-600 text-white shadow-sm'
                            : 'hover:text-blue-700'
                        }`}
                      >
                        <Clock className="w-3 h-3" />
                        <span>In Progress ({waitingPRs.length})</span>
                      </button>
                      <button
                        onClick={() => setDashboardQueueFilter('HISTORY')}
                        className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                          dashboardQueueFilter === 'HISTORY'
                            ? 'bg-emerald-600 text-white shadow-sm'
                            : 'hover:text-emerald-700'
                        }`}
                      >
                        <History className="w-3 h-3" />
                        <span>History ({historyPRs.length})</span>
                      </button>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                          <th className="py-2.5 px-3">Reference</th>
                          <th className="py-2.5 px-3">Requester & Dept</th>
                          <th className="py-2.5 px-3">Item & Qty</th>
                          <th className="py-2.5 px-3">Selected Supplier</th>
                          <th className="py-2.5 px-3">Workflow State</th>
                          <th className="py-2.5 px-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {getDashboardPRs().length === 0 ? (
                          <tr>
                            <td colSpan={6} className="py-8 text-center text-slate-400 font-medium">
                              No requests in this queue category.
                            </td>
                          </tr>
                        ) : (
                          getDashboardPRs().map(pr => {
                            const stateInfo = getWorkflowState(pr.status);
                            const act = getPrimaryAction(pr, role);
                            const isActionOwner = categorizePRForRole(pr, role) === 'ACTION_REQUIRED';

                            return (
                              <tr key={pr.id} className={`hover:bg-slate-50 transition ${isActionOwner ? 'bg-amber-50/20' : ''}`}>
                                <td className="py-3 px-3">
                                  <span className="font-bold text-slate-900 block">{pr.reference_number}</span>
                                  <span className="text-[10px] text-slate-400">{new Date(pr.created_at).toLocaleDateString()}</span>
                                </td>
                                <td className="py-3 px-3">
                                  <span className="font-semibold text-slate-800 block">{pr.requester_name}</span>
                                  <span className="text-slate-400 text-[10px]">{pr.department_name}</span>
                                </td>
                                <td className="py-3 px-3">
                                  <span className="font-semibold text-slate-800">{pr.item_name}</span>
                                  <span className="text-slate-400 block text-[10px]">{pr.quantity} {pr.item_unit}</span>
                                </td>
                                <td className="py-3 px-3 font-medium text-slate-700">{pr.selected_vendor_name}</td>
                                <td className="py-3 px-3">
                                  <span className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border inline-block ${stateInfo.badgeStyle}`}>
                                    {stateInfo.label}
                                  </span>
                                </td>
                                <td className="py-3 px-3 text-right space-x-2">
                                  {act.type === 'REVISE' && (
                                    <button
                                      onClick={() => handleOpenReviseModal(pr)}
                                      className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-bold transition inline-flex items-center space-x-1 shadow-sm"
                                    >
                                      <RotateCcw className="w-3 h-3" />
                                      <span>Revise & Resubmit</span>
                                    </button>
                                  )}

                                  {act.type === 'EVALUATE' && (
                                    <button
                                      onClick={() => handleOpenQuotationComparison(pr)}
                                      className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold transition inline-flex items-center space-x-1 shadow-sm"
                                    >
                                      <Sparkles className="w-3 h-3" />
                                      <span>Evaluate Bids</span>
                                    </button>
                                  )}

                                  <button
                                    onClick={() => handleOpenCheckingSheet(pr.id)}
                                    className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition inline-flex items-center space-x-1"
                                  >
                                    <Eye className="w-3.5 h-3.5 text-slate-500" />
                                    <span>Checking Sheet</span>
                                  </button>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )
          )}

          {/* TAB 2: PURCHASE REQUESTS LIST */}
          {currentTab === 'requests' && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900">Purchase Request Management</h2>
                  <p className="text-xs text-slate-500">Comprehensive queue management separated by role action ownership</p>
                </div>
                {(role === 'EMPLOYEE' || role === 'ADMIN') && (
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="px-4 py-2 rounded-xl bg-blue-600 text-white font-bold text-xs shadow-md shadow-blue-500/20 hover:bg-blue-700 transition flex items-center space-x-1.5"
                  >
                    <FilePlus className="w-4 h-4" />
                    <span>New Purchase Request</span>
                  </button>
                )}
              </div>

              {/* Toolbar: Queue Filters & Search */}
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pt-1">
                <div className="flex items-center p-1 bg-slate-100 rounded-xl space-x-1 text-xs font-bold text-slate-600 overflow-x-auto">
                  <button
                    onClick={() => setRequestsQueueFilter('ALL')}
                    className={`px-3 py-1.5 rounded-lg transition ${
                      requestsQueueFilter === 'ALL'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'hover:text-slate-900'
                    }`}
                  >
                    All ({prs.length})
                  </button>
                  <button
                    onClick={() => setRequestsQueueFilter('ACTION_REQUIRED')}
                    className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                      requestsQueueFilter === 'ACTION_REQUIRED'
                        ? 'bg-amber-500 text-white shadow-sm'
                        : 'hover:text-amber-700'
                    }`}
                  >
                    <Zap className="w-3 h-3" />
                    <span>Action Required ({actionRequiredPRs.length})</span>
                  </button>
                  <button
                    onClick={() => setRequestsQueueFilter('WAITING')}
                    className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                      requestsQueueFilter === 'WAITING'
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'hover:text-blue-700'
                    }`}
                  >
                    <Clock className="w-3 h-3" />
                    <span>In Progress ({waitingPRs.length})</span>
                  </button>
                  <button
                    onClick={() => setRequestsQueueFilter('HISTORY')}
                    className={`px-3 py-1.5 rounded-lg transition flex items-center space-x-1 ${
                      requestsQueueFilter === 'HISTORY'
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : 'hover:text-emerald-700'
                    }`}
                  >
                    <History className="w-3 h-3" />
                    <span>History ({historyPRs.length})</span>
                  </button>
                </div>

                <div className="relative w-full md:w-64">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search requests, items, status..."
                    className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                      <th className="py-3 px-3">Reference</th>
                      <th className="py-3 px-3">Requester</th>
                      <th className="py-3 px-3">Department</th>
                      <th className="py-3 px-3">Item & Qty</th>
                      <th className="py-3 px-3">Selected Supplier</th>
                      <th className="py-3 px-3">Workflow State</th>
                      <th className="py-3 px-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {getRequestsPRs().length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-400 font-medium">
                          No purchase requests found matching the selected queue/filter.
                        </td>
                      </tr>
                    ) : (
                      getRequestsPRs().map(pr => {
                        const stateInfo = getWorkflowState(pr.status);
                        const act = getPrimaryAction(pr, role);
                        const isActionOwner = categorizePRForRole(pr, role) === 'ACTION_REQUIRED';

                        return (
                          <tr key={pr.id} className={`hover:bg-slate-50 transition ${isActionOwner ? 'bg-amber-50/20' : ''}`}>
                            <td className="py-3.5 px-3">
                              <span className="font-bold text-slate-900 block">{pr.reference_number}</span>
                              <span className="text-[10px] text-slate-400">{new Date(pr.created_at).toLocaleDateString()}</span>
                            </td>
                            <td className="py-3.5 px-3 text-slate-700 font-medium">{pr.requester_name}</td>
                            <td className="py-3.5 px-3 text-slate-600">{pr.department_name}</td>
                            <td className="py-3.5 px-3">
                              <span className="font-semibold text-slate-800">{pr.item_name}</span>
                              <span className="text-slate-400 block text-[10px]">{pr.quantity} {pr.item_unit}</span>
                            </td>
                            <td className="py-3.5 px-3 font-medium text-slate-700">{pr.selected_vendor_name}</td>
                            <td className="py-3.5 px-3">
                              <span className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border inline-block ${stateInfo.badgeStyle}`}>
                                {stateInfo.label}
                              </span>
                            </td>
                            <td className="py-3.5 px-3 text-right space-x-2">
                              {act.type === 'REVISE' && (
                                <button
                                  onClick={() => handleOpenReviseModal(pr)}
                                  className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-bold transition inline-flex items-center space-x-1 shadow-sm"
                                >
                                  <RotateCcw className="w-3.5 h-3.5" />
                                  <span>Revise & Resubmit</span>
                                </button>
                              )}

                              {act.type === 'EVALUATE' && (
                                <button
                                  onClick={() => handleOpenQuotationComparison(pr)}
                                  className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold transition inline-flex items-center space-x-1 shadow-sm"
                                >
                                  <Sparkles className="w-3.5 h-3.5" />
                                  <span>Evaluate Bids</span>
                                </button>
                              )}

                              <button
                                onClick={() => handleOpenCheckingSheet(pr.id)}
                                className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-xs font-bold transition inline-flex items-center space-x-1"
                              >
                                <Eye className="w-3.5 h-3.5" />
                                <span>Checking Sheet</span>
                              </button>

                              {pr.status !== 'PO_GENERATED' && pr.status !== 'COMPLETED' && (role === 'ADMIN' || (role === 'EMPLOYEE' && pr.status === 'DRAFT')) && (
                                <button
                                  onClick={() => handleDeletePR(pr.id, pr.reference_number)}
                                  className="px-2.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg text-xs font-bold transition inline-flex items-center space-x-1"
                                  title="Delete Request"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  <span>Delete</span>
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 3: RFQs & QUOTATIONS */}
          {currentTab === 'rfqs' && (
            <div className="space-y-6">
              {role === 'VENDOR' ? (
                <VendorPortal rfqs={rfqs} onRefresh={refreshAllData} />
              ) : (
                <>
                  {selectedPrForQuotes ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <button
                          onClick={() => {
                            setSelectedPrForQuotes(null);
                            setQuotationAnalysis(null);
                          }}
                          className="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg text-xs font-bold transition flex items-center space-x-1"
                        >
                          <span>← Back to All RFQs</span>
                        </button>
                      </div>
                      <QuotationComparison
                        analysis={quotationAnalysis && quotationAnalysis.purchase_request_id === selectedPrForQuotes.id ? quotationAnalysis : null}
                        pr={selectedPrForQuotes}
                        onRefresh={refreshAllData}
                        userRole={role}
                      />
                    </div>
                  ) : (
                    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                        <div>
                          <h3 className="text-base font-bold text-slate-900">Active Requests for Quotation (RFQs)</h3>
                          <p className="text-xs text-slate-500">Multi-supplier competitive bidding tracking and quotation arrivals</p>
                        </div>
                      </div>

                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                              <th className="py-2.5 px-3">RFQ Reference</th>
                              <th className="py-2.5 px-3">PR Reference</th>
                              <th className="py-2.5 px-3">Target Supplier</th>
                              <th className="py-2.5 px-3">Item & Qty</th>
                              <th className="py-2.5 px-3">Deadline</th>
                              <th className="py-2.5 px-3">Quote Status</th>
                              <th className="py-2.5 px-3 text-right">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {rfqs.length === 0 ? (
                              <tr>
                                <td colSpan={7} className="py-8 text-center text-slate-400">
                                  No RFQs currently dispatched.
                                </td>
                              </tr>
                            ) : (
                              rfqs.map(rfq => {
                                const matchingPr = prs.find(p => p.id === rfq.purchase_request_id);
                                return (
                                  <tr key={rfq.id} className="hover:bg-slate-50 transition">
                                    <td className="py-3 px-3 font-bold text-slate-900">{rfq.reference_number}</td>
                                    <td className="py-3 px-3 font-semibold text-blue-700">{rfq.pr_reference}</td>
                                    <td className="py-3 px-3 font-medium text-slate-700">{rfq.vendor_name}</td>
                                    <td className="py-3 px-3 text-slate-600">
                                      {rfq.item_name} ({rfq.quantity} {rfq.item_unit})
                                    </td>
                                    <td className="py-3 px-3 text-slate-500">
                                      {rfq.due_at ? new Date(rfq.due_at).toLocaleDateString() : '7 Days'}
                                    </td>
                                    <td className="py-3 px-3">
                                      {rfq.has_quotation ? (
                                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                          Quote Submitted
                                        </span>
                                      ) : (
                                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
                                          Awaiting Quote
                                        </span>
                                      )}
                                    </td>
                                    <td className="py-3 px-3 text-right">
                                      {(role === 'SUPERVISOR' || role === 'ADMIN') && matchingPr && (
                                        <button
                                          onClick={() => handleOpenQuotationComparison(matchingPr)}
                                          className="px-2.5 py-1 bg-purple-100 hover:bg-purple-200 text-purple-800 rounded-lg text-xs font-bold transition"
                                        >
                                          Compare Quotes
                                        </button>
                                      )}
                                    </td>
                                  </tr>
                                );
                              })
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* TAB 4: PURCHASE ORDERS */}
          {currentTab === 'orders' && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-900">Official Purchase Orders (POs)</h3>
                  <p className="text-xs text-slate-500">Immutable, legally binding purchase commitments with generated PDF documents</p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
                      <th className="py-2.5 px-3">PO Number</th>
                      <th className="py-2.5 px-3">PR Reference</th>
                      <th className="py-2.5 px-3">Awarded Supplier</th>
                      <th className="py-2.5 px-3">Item & Qty</th>
                      <th className="py-2.5 px-3">Total Amount</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Document</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {orders.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-400">
                          No Purchase Orders generated yet.
                        </td>
                      </tr>
                    ) : (
                      orders.map(po => (
                        <tr key={po.id} className="hover:bg-slate-50 transition">
                          <td className="py-3 px-3 font-bold text-slate-900">{po.po_number}</td>
                          <td className="py-3 px-3 font-semibold text-blue-700">{po.pr_reference}</td>
                          <td className="py-3 px-3 font-medium text-slate-700">{po.vendor_name}</td>
                          <td className="py-3 px-3 text-slate-600">
                            {po.item_name} ({po.quantity} {po.item_unit})
                          </td>
                          <td className="py-3 px-3 font-bold text-slate-900">
                            ${(po.approved_amount ?? po.total_amount ?? 0).toLocaleString()}
                          </td>
                          <td className="py-3 px-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                              {po.status}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={() => api.downloadPO(po.id, po.po_number)}
                              className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 rounded-lg text-xs font-bold transition inline-flex items-center space-x-1.5"
                            >
                              <Download className="w-3.5 h-3.5" />
                              <span>Download PDF</span>
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 5: VENDOR DIRECTORY */}
          {currentTab === 'vendors' && (
            <div className="space-y-6">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                <h3 className="text-base font-bold text-slate-900 mb-1">Approved Supplier Network</h3>
                <p className="text-xs text-slate-500 mb-4">Enterprise supplier catalog with quality ratings, SLA reliability, and performance badges</p>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {DEMO_USERS.filter(u => u.role === 'VENDOR').map(v => (
                    <div key={v.email} className="p-4 rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition bg-white space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-bold text-sm text-slate-900">{v.label}</h4>
                          <span className="text-xs text-slate-400">{v.email}</span>
                        </div>
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-[10px] font-bold rounded">
                          Active Supplier
                        </span>
                      </div>
                      <div className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                        <span>Direct portal access to submit quotations on dispatched RFQs.</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </main>
      </div>

      {/* Floating AI Assistant Trigger (Supervisor & Admin only) */}
      {(role === 'SUPERVISOR' || role === 'ADMIN') && (
        <button
          onClick={() => setShowCopilot(true)}
          className="fixed bottom-6 right-6 p-3.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-full shadow-2xl hover:scale-105 transition-transform flex items-center space-x-2 z-40 border border-white/20"
          title="Open AI Assistant"
        >
          <Sparkles className="w-5 h-5 animate-pulse" />
          <span className="text-xs font-bold pr-1 hidden sm:inline">AI Assistant</span>
        </button>
      )}

      {/* Modals and Drawers */}
      <CreatePRModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={refreshAllData}
        items={items}
      />

      <CheckingSheet
        pr={selectedPrDetail}
        isOpen={showCheckingSheet}
        onClose={() => setShowCheckingSheet(false)}
        onRefresh={refreshAllData}
        userRole={role}
        onOpenRevise={handleOpenReviseModal}
      />

      <RevisePRModal
        pr={selectedPrForRevise}
        isOpen={showReviseModal}
        onClose={() => setShowReviseModal(false)}
        onSuccess={refreshAllData}
      />

      <SubmitQuotationModal
        isOpen={showQuoteModal}
        rfq={selectedRfqForQuote}
        onClose={() => {
          setShowQuoteModal(false);
          setSelectedRfqForQuote(null);
        }}
        onSuccess={refreshAllData}
      />

      {(role === 'SUPERVISOR' || role === 'ADMIN') && (
        <AICopilotDrawer
          isOpen={showCopilot}
          onClose={() => setShowCopilot(false)}
          activePrId={selectedPrDetail?.id || prs[0]?.id}
          activePrRef={selectedPrDetail?.reference_number || prs[0]?.reference_number}
        />
      )}

    </div>
  );
}
