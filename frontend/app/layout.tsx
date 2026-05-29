import {
  Activity,
  BookOpen,
  Boxes,
  BrainCircuit,
  ClipboardCheck,
  Database,
  FlaskConical,
  Home,
  LineChart,
  Library,
  RefreshCw,
  Settings,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import "./styles.css";

const navItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/research-programs", label: "Research Programs", icon: BrainCircuit },
  { href: "/data-assets", label: "Data Assets", icon: Database },
  { href: "/experiments", label: "Experiments", icon: FlaskConical },
  { href: "/training-runs", label: "Training Runs", icon: LineChart },
  { href: "/models-checkpoints", label: "Models & Checkpoints", icon: Boxes },
  { href: "/evaluations", label: "Evaluations", icon: ClipboardCheck },
  { href: "/inference-observability", label: "Inference Observability", icon: Activity },
  { href: "/failure-library", label: "Failure Library", icon: Library },
  { href: "/dataset-iterations", label: "Dataset Iterations", icon: RefreshCw },
  { href: "/workspace", label: "Workspace", icon: Workflow },
  { href: "/docs", label: "Docs", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
];

export const metadata = {
  title: "Research Data Command Center",
  description: "Lineage-first research operations platform for AI research lifecycles.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <Link className="brand" href="/">
              <span className="brand-mark" aria-hidden="true">
                <span className="brand-node brand-node-primary" />
                <span className="brand-node brand-node-mid" />
                <span className="brand-node brand-node-end" />
              </span>
              <span className="brand-copy">
                <span>Research Data</span>
                <span>Command Center</span>
              </span>
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
            <div className="site-signature">Built by Ning Han</div>
          </aside>
          <main className="main">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
