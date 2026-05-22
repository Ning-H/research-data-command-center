import {
  BookOpen,
  Bot,
  Database,
  FileText,
  Home,
  LineChart,
  Settings,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import "./styles.css";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/datasets", label: "Datasets", icon: Database },
  { href: "/runs", label: "Runs", icon: LineChart },
  { href: "/models", label: "Models & Evaluations", icon: Bot },
  { href: "/workspace", label: "Workspace", icon: Workflow },
  { href: "/docs", label: "Docs", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
];

export const metadata = {
  title: "Research Data Command Center",
  description: "Research data platform for datasets, runs, models, and evaluations.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <Link className="brand" href="/">
              <FileText aria-hidden="true" size={22} />
              <span>Research Data Command Center</span>
            </Link>
            <nav className="nav-list" aria-label="Main navigation">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link className="nav-item" href={item.href} key={item.href}>
                    <Icon aria-hidden="true" size={18} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
