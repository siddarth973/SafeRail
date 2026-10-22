import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  CheckSquare,
  HeartPulse,
  FileText,
  FileCheck2,
  Settings,
  ChevronDown
} from 'lucide-react';

interface SidebarProps {
  pendingCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ pendingCount = 7 }) => {
  const navItems = [
    { name: 'Overview', to: '/', icon: LayoutDashboard },
    { name: 'Action Approvals', to: '/approvals', icon: CheckSquare, badge: pendingCount },
    { name: 'Oversight Health', to: '/oversight', icon: HeartPulse },
    { name: 'Audit Trail', to: '/audit', icon: FileText },
    { name: 'Evidence Reports', to: '/evidence', icon: FileCheck2 },
    { name: 'Settings', to: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#0a101d] border-r border-[#19253d] flex flex-col justify-between shrink-0 select-none min-h-screen">
      {/* Top Logo & Product Info */}
      <div>
        <div className="p-5 flex items-center gap-3 border-b border-[#141f33]/60">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/40 flex items-center justify-center shadow-[0_0_12px_rgba(6,182,212,0.3)]">
            <svg className="w-5 h-5 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight">SafeRail</h1>
            <p className="text-[11px] text-slate-400 -mt-0.5 font-medium">AI Agent Safety & Control</p>
          </div>
        </div>

        {/* Navigation List */}
        <nav className="p-3 space-y-1.5 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-[#123869] text-white shadow-[0_0_12px_rgba(37,99,235,0.25)] border border-blue-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#0f1a2e]'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center gap-3">
                      <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                      <span>{item.name}</span>
                    </div>
                    {item.badge !== undefined && (
                      <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-600 text-white shadow-sm">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom: Reviewer Profile */}
      <div className="p-4 border-t border-[#141f33]/80">
        <div className="flex items-center justify-between p-2 rounded-lg hover:bg-[#111c30] cursor-pointer transition-colors group">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#1e293b] border border-[#2b3b55] flex items-center justify-center font-bold text-white text-xs">
              K
            </div>
            <div>
              <div className="text-xs font-semibold text-white group-hover:text-cyan-300 transition-colors">
                Kavya Sharma
              </div>
              <div className="text-[11px] text-slate-400">Admin</div>
            </div>
          </div>
          <ChevronDown className="w-4 h-4 text-slate-400 group-hover:text-slate-200" />
        </div>
      </div>
    </aside>
  );
};
