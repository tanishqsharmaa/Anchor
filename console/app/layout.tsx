import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PROJECT ANCHOR // Indian Naval Tactical Regulatory Intelligence",
  description:
    "Autonomous Naval Compliance Hub for Operational Regulation — INICAI 2026 Sovereign Defence AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark bg-[#0B0F19]">
      <body className="bg-[#0B0F19] text-[#E5E7EB] min-h-screen antialiased flex flex-col font-sans selection:bg-[#00E5FF]/30 selection:text-white">
        {/* Top Security Classification Banner */}
        <div className="w-full bg-[#0E1726] border-b border-[#233554] py-1 px-4 text-center">
          <div className="flex items-center justify-between text-[11px] font-mono tracking-widest text-[#94A3B8]">
            <span className="hidden sm:inline text-[#00E5FF]">
              INICAI 2026 // DEFENCE REGULATORY INTELLIGENCE
            </span>
            <span className="text-[#FFD700] font-bold mx-auto sm:mx-0">
              RESTRICTED // FOR OFFICIAL USE ONLY (NAVY REGS / DFPDS-2026)
            </span>
            <span className="hidden sm:inline text-[#10B981]">
              SOVEREIGN AIR-GAPPED SYSTEM
            </span>
          </div>
        </div>

        {/* Application Shell */}
        <div className="flex-1 flex flex-col">{children}</div>

        {/* Bottom Classification & Status Bar */}
        <footer className="w-full bg-[#0E1726] border-t border-[#233554] py-1.5 px-6 flex items-center justify-between text-[11px] font-mono text-[#64748B]">
          <div className="flex items-center space-x-3">
            <span className="flex items-center space-x-1.5 text-[#10B981]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#10B981] animate-pulse" />
              <span>NODE: LOCAL AIR-GAP (INTEL LUNAR LAKE)</span>
            </span>
            <span className="text-[#233554]">|</span>
            <span>MODELS: BGE-M3 (INT8) · RERANKER (INT8) · DEBERTA-V3 (INT8) · QWEN2.5-7B</span>
          </div>
          <div className="text-[#94A3B8]">
            <span>ANCHOR TACTICAL CONSOLE v1.0.0</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
