import React from "react";

export type BadgeVariant =
  | "cyan"
  | "gold"
  | "green"
  | "amber"
  | "red"
  | "slate"
  | "certified"
  | "regen"
  | "abstain";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  dot?: boolean;
}

const variantStyles: Record<BadgeVariant, string> = {
  cyan: "border-[#00E5FF]/40 text-[#00E5FF] bg-[#00E5FF]/10",
  gold: "border-[#FFD700]/40 text-[#FFD700] bg-[#FFD700]/10",
  green: "border-[#10B981]/40 text-[#10B981] bg-[#10B981]/10",
  certified: "border-[#10B981]/50 text-[#10B981] bg-[#10B981]/15 font-semibold",
  amber: "border-[#F59E0B]/40 text-[#F59E0B] bg-[#F59E0B]/10",
  regen: "border-[#F59E0B]/50 text-[#F59E0B] bg-[#F59E0B]/15",
  red: "border-[#EF4444]/40 text-[#EF4444] bg-[#EF4444]/10",
  abstain: "border-[#EF4444]/50 text-[#EF4444] bg-[#EF4444]/15 font-semibold",
  slate: "border-[#233554] text-[#94A3B8] bg-[#111C2E]",
};

const dotColors: Record<BadgeVariant, string> = {
  cyan: "bg-[#00E5FF]",
  gold: "bg-[#FFD700]",
  green: "bg-[#10B981]",
  certified: "bg-[#10B981]",
  amber: "bg-[#F59E0B]",
  regen: "bg-[#F59E0B]",
  red: "bg-[#EF4444]",
  abstain: "bg-[#EF4444]",
  slate: "bg-[#64748B]",
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "cyan",
  size = "sm",
  dot = false,
  className = "",
  ...props
}) => {
  const sizeClasses = size === "sm" ? "text-xs px-2 py-0.5" : "text-sm px-2.5 py-1";
  const style = variantStyles[variant] || variantStyles.cyan;
  const dotColor = dotColors[variant] || dotColors.cyan;

  return (
    <span
      className={`inline-flex items-center space-x-1.5 rounded border tracking-wider font-mono uppercase transition-colors ${sizeClasses} ${style} ${className}`}
      {...props}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dotColor} animate-pulse`} />}
      <span>{children}</span>
    </span>
  );
};
