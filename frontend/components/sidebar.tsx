
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LayoutDashboard, AlertTriangle, Cpu } from "lucide-react";
import { socket } from "@/lib/websocket";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/incidents", label: "Incidents", icon: AlertTriangle },
];

export function Sidebar() {
  const path = usePathname();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    socket.connect();
    const tick = setInterval(() => setConnected(socket.isConnected), 1000);
    return () => clearInterval(tick);
  }, []);

  return (
    <aside className="w-56 shrink-0 flex flex-col border-r border-[--border] bg-[--bg-surface]">
      <div className="px-5 py-5 border-b border-[--border]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-indigo-600 flex items-center justify-center">
            <Cpu size={14} className="text-white" />
          </div>
          <span className="font-semibold text-sm tracking-wide text-slate-100">
            OpsPilot
          </span>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            path === href ||
            (href !== "/dashboard" && path.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`
                flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors
                ${
                  active
                    ? "bg-[--accent-dim] text-indigo-300"
                    : "text-[--text-secondary] hover:text-slate-200 hover:bg-[--bg-elevated]"
                }
              `}
            >
              <Icon size={15} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-3 border-t border-[--border]">
        <div className="flex items-center gap-2">
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected ? "bg-green-500" : "bg-slate-600"
            }`}
          />
          <span className="text-xs text-[--text-muted] font-mono">
            {connected ? "live" : "connecting..."}
          </span>
        </div>
      </div>
    </aside>
  );
}