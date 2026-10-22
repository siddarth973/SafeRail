import React, { useState } from 'react';
import { Search, Bell, Settings, Languages } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface TopHeaderProps {
  onSearch?: (query: string) => void;
  isGatewayOnline?: boolean;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  onSearch,
  isGatewayOnline = true,
}) => {
  const { i18n } = useTranslation();
  const [searchVal, setSearchVal] = useState('');
  const [showLangMenu, setShowLangMenu] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchVal(e.target.value);
    if (onSearch) onSearch(e.target.value);
  };

  const changeLanguage = (lang: string) => {
    i18n.changeLanguage(lang);
    setShowLangMenu(false);
  };

  return (
    <header className="h-20 px-8 border-b border-[#141f33] bg-[#080d19]/90 backdrop-blur-md flex items-center justify-between sticky top-0 z-30">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">Security Operations</h1>
        <p className="text-xs text-slate-400 mt-0.5">Monitor, control and keep your AI agents safe.</p>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Search Input */}
        <div className="relative w-64 md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchVal}
            onChange={handleSearchChange}
            placeholder="Search actions, agents, users..."
            className="w-full bg-[#0d1527] border border-[#19253d] focus:border-cyan-500/60 focus:outline-none rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 transition-colors shadow-inner"
          />
        </div>

        {/* Gateway Online Status Pill */}
        <div className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#10b981]" />
          <div className="flex flex-col text-left">
            <span className="text-xs font-bold text-emerald-400 leading-tight">
              {isGatewayOnline ? 'Gateway Online' : 'Gateway Offline'}
            </span>
            <span className="text-[10px] text-emerald-500/80 leading-tight">All systems operational</span>
          </div>
        </div>

        {/* Language Switcher (EN, KN, HI) */}
        <div className="relative">
          <button
            onClick={() => setShowLangMenu(!showLangMenu)}
            className="p-2 rounded-lg bg-[#0d1527] border border-[#19253d] text-slate-400 hover:text-slate-200 hover:bg-[#121c32] transition-colors"
            title="Switch Language"
          >
            <Languages className="w-4 h-4" />
          </button>

          {showLangMenu && (
            <div className="absolute right-0 mt-2 w-36 bg-[#0d1527] border border-[#19253d] rounded-lg shadow-xl py-1 z-50 text-xs">
              <button
                onClick={() => changeLanguage('en')}
                className={`w-full px-3 py-1.5 text-left hover:bg-[#152038] ${i18n.language === 'en' ? 'text-cyan-400 font-semibold' : 'text-slate-300'}`}
              >
                English
              </button>
              <button
                onClick={() => changeLanguage('kn')}
                className={`w-full px-3 py-1.5 text-left hover:bg-[#152038] ${i18n.language === 'kn' ? 'text-cyan-400 font-semibold' : 'text-slate-300'}`}
              >
                ಕನ್ನಡ (Kannada)
              </button>
              <button
                onClick={() => changeLanguage('hi')}
                className={`w-full px-3 py-1.5 text-left hover:bg-[#152038] ${i18n.language === 'hi' ? 'text-cyan-400 font-semibold' : 'text-slate-300'}`}
              >
                हिन्दी (Hindi)
              </button>
            </div>
          )}
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setNotificationOpen(!notificationOpen)}
            className="p-2 rounded-lg bg-[#0d1527] border border-[#19253d] text-slate-400 hover:text-slate-200 hover:bg-[#121c32] transition-colors relative"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="w-2 h-2 rounded-full bg-rose-500 absolute top-1.5 right-1.5 shadow-[0_0_6px_#ef4444]" />
          </button>

          {notificationOpen && (
            <div className="absolute right-0 mt-2 w-72 bg-[#0d1527] border border-[#19253d] rounded-xl shadow-2xl p-3 z-50 text-xs">
              <div className="font-semibold text-white mb-2 pb-1 border-b border-[#19253d] flex justify-between items-center">
                <span>Security Alerts</span>
                <span className="text-[10px] text-cyan-400">1 Unread</span>
              </div>
              <div className="space-y-2">
                <div className="p-2 rounded bg-rose-950/30 border border-rose-900/40 text-slate-200">
                  <div className="font-medium text-rose-400">Action Blocked</div>
                  <div className="text-[11px] text-slate-400">Demo Agent attempted unauthorized email dispatch.</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Settings Button */}
        <button
          className="p-2 rounded-lg bg-[#0d1527] border border-[#19253d] text-slate-400 hover:text-slate-200 hover:bg-[#121c32] transition-colors"
          title="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
