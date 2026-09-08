'use client';

import React, { useState, useRef, useEffect } from 'react';
import { api } from '../lib/api';
import { Sparkles, Send, X, Bot, User, Trash2, ArrowRight } from 'lucide-react';

interface AICopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activePrId?: string;
  activePrRef?: string;
}

export const AICopilotDrawer: React.FC<AICopilotDrawerProps> = ({
  isOpen,
  onClose,
  activePrId,
  activePrRef
}) => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'assistant'; text: string; time: string }>>([
    {
      sender: 'assistant',
      text: "Hello! I'm your AI Procurement Assistant. How can I help you today? You can ask me about purchase orders, suppliers, inventory, request statuses, or anything else.",
      time: 'Just now'
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  if (!isOpen) return null;

  const handleSend = async (customText?: string) => {
    const textToSend = customText || query;
    if (!textToSend.trim()) return;

    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const newMsgs = [...messages, { sender: 'user' as const, text: textToSend, time: currentTime }];
    setMessages(newMsgs);
    if (!customText) setQuery('');
    setIsLoading(true);

    try {
      const chatRes = await api.aiChat(textToSend, activePrId ? 'pr' : undefined, activePrId);
      setMessages([
        ...newMsgs,
        {
          sender: 'assistant',
          text: chatRes.reply,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch (err: any) {
      setMessages([
        ...newMsgs,
        {
          sender: 'assistant',
          text: 'I am temporarily unable to connect to the AI model service. Please try again in a moment.',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([
      {
        sender: 'assistant',
        text: "Chat cleared. How can I assist you with your procurement tasks?",
        time: 'Just now'
      }
    ]);
  };

  const suggestedPrompts = [
    ...(activePrRef ? [`Tell me about PR ${activePrRef}`] : []),
    'Show me recent purchase orders and awarded suppliers',
    'What is the status of our active purchase requests?',
    'Which suppliers do we have for hardware and networking?',
    'How does the multi-factor quotation evaluation score vendors?'
  ];

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[440px] bg-white shadow-2xl border-l border-slate-200 z-50 flex flex-col animate-in slide-in-from-right duration-200">
      
      {/* Top Header */}
      <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/90 backdrop-blur">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-purple-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 border-2 border-white rounded-full"></span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="font-bold text-sm text-slate-900">AI Assistant</h3>
              <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-purple-100 text-purple-700">Copilot</span>
            </div>
            <p className="text-[11px] text-slate-500">Ask anything about orders, suppliers & requests</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-1">
          <button
            onClick={handleClearChat}
            className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-xl transition"
            title="Clear conversation"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-xl transition"
            title="Close Assistant"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Suggested Quick Prompts (shown when 1 message) */}
      {messages.length <= 1 && (
        <div className="p-3.5 bg-purple-50/40 border-b border-purple-100/60 space-y-2">
          <span className="text-[10px] font-bold text-purple-900 uppercase tracking-wider block">Suggested Questions</span>
          <div className="flex flex-col gap-1.5">
            {suggestedPrompts.slice(0, 3).map((prompt, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(prompt)}
                className="text-left px-3 py-1.5 bg-white hover:bg-purple-100/60 border border-purple-200/80 rounded-xl text-xs font-medium text-slate-700 transition flex items-center justify-between group shadow-2xs"
              >
                <span className="truncate pr-2">{prompt}</span>
                <ArrowRight className="w-3 h-3 text-purple-400 group-hover:text-purple-700 shrink-0 transition" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat Messages Body */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-slate-50/40">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-2.5 ${m.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
          >
            <div className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold ${
              m.sender === 'user'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-purple-600 text-white shadow-sm'
            }`}>
              {m.sender === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
            </div>

            <div className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'} max-w-[82%]`}>
              <div
                className={`p-3.5 rounded-2xl text-xs leading-relaxed shadow-2xs ${
                  m.sender === 'user'
                    ? 'bg-blue-600 text-white font-medium rounded-tr-none'
                    : 'bg-white text-slate-800 rounded-tl-none border border-slate-200'
                }`}
              >
                <div className="whitespace-pre-line">{m.text}</div>
              </div>
              <span className="text-[10px] text-slate-400 mt-1 px-1">{m.time}</span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-start gap-2.5">
            <div className="w-7 h-7 rounded-xl bg-purple-600 text-white flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="p-3.5 bg-white border border-slate-200 rounded-2xl rounded-tl-none text-xs text-slate-500 flex items-center space-x-2 shadow-2xs">
              <Sparkles className="w-3.5 h-3.5 animate-spin text-purple-600 shrink-0" />
              <span>Thinking and searching records...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <div className="p-3.5 border-t border-slate-200 bg-white">
        <form
          onSubmit={e => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Type a message or ask a question..."
            disabled={isLoading}
            className="flex-1 px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-800 focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="p-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl transition shadow-md shadow-purple-600/20 disabled:opacity-40 disabled:shadow-none cursor-pointer"
            title="Send message"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
};
