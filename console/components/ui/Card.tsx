import React from "react";

export type CardGlow = "none" | "cyan" | "gold" | "green";

interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  glow?: CardGlow;
  title?: React.ReactNode;
  headerRight?: React.ReactNode;
}

const glowStyles: Record<CardGlow, string> = {
  none: "border-[#233554]",
  cyan: "border-[#00E5FF]/50 shadow-[0_0_15px_rgba(0,229,255,0.15)]",
  gold: "border-[#FFD700]/50 shadow-[0_0_15px_rgba(255,215,0,0.15)]",
  green: "border-[#10B981]/50 shadow-[0_0_15px_rgba(16,185,129,0.15)]",
};

export const Card: React.FC<CardProps> = ({
  children,
  title,
  headerRight,
  glow = "none",
  className = "",
  ...props
}) => {
  return (
    <div
      className={`bg-[#111C2E] rounded-lg border flex flex-col transition-all duration-200 ${glowStyles[glow]} ${className}`}
      {...props}
    >
      {(title || headerRight) && (
        <div className="flex items-center justify-between border-b border-[#233554] px-4 py-3">
          {typeof title === "string" ? (
            <h3 className="text-sm font-semibold tracking-wider text-[#CCD6F6] uppercase font-mono">
              {title}
            </h3>
          ) : (
            title
          )}
          {headerRight && <div>{headerRight}</div>}
        </div>
      )}
      <div className="p-4 flex-1 flex flex-col">{children}</div>
    </div>
  );
};
