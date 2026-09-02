import React from "react";

export type ButtonVariant = "primary" | "secondary" | "gold" | "danger" | "ghost" | "outline" | "cyan" | "green";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-[#00E5FF] text-[#0B0F19] font-bold hover:bg-[#00B8D4] active:bg-[#0097A7] border border-[#00E5FF] shadow-[0_0_10px_rgba(0,229,255,0.2)]",
  cyan:
    "bg-[#00E5FF] text-[#0B0F19] font-bold hover:bg-[#00B8D4] active:bg-[#0097A7] border border-[#00E5FF] shadow-[0_0_10px_rgba(0,229,255,0.2)]",
  secondary:
    "bg-[#162032] text-[#CCD6F6] hover:text-white hover:bg-[#1F2E47] border border-[#233554] active:bg-[#111C2E]",
  outline:
    "bg-transparent text-[#CCD6F6] hover:text-[#00E5FF] hover:border-[#00E5FF]/60 border border-[#233554] active:bg-[#162032]",
  gold:
    "bg-[#FFD700]/10 text-[#FFD700] border border-[#FFD700]/50 hover:bg-[#FFD700]/20 active:bg-[#FFD700]/30 shadow-[0_0_10px_rgba(255,215,0,0.15)]",
  green:
    "bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/50 hover:bg-[#10B981]/25 active:bg-[#10B981]/35 shadow-[0_0_10px_rgba(16,185,129,0.15)]",
  danger:
    "bg-[#EF4444]/15 text-[#EF4444] border border-[#EF4444]/50 hover:bg-[#EF4444]/25 active:bg-[#EF4444]/35",
  ghost:
    "bg-transparent text-[#94A3B8] hover:text-white hover:bg-[#162032] border border-transparent",
};


const sizeClasses: Record<ButtonSize, string> = {
  sm: "text-xs px-2.5 py-1.5 rounded",
  md: "text-sm px-4 py-2 rounded",
  lg: "text-base px-6 py-2.5 rounded",
};

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = "primary",
  size = "md",
  isLoading = false,
  leftIcon,
  rightIcon,
  className = "",
  disabled,
  ...props
}) => {
  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center space-x-2 font-mono tracking-wide transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-[#00E5FF] focus:ring-offset-2 focus:ring-offset-[#0B0F19] disabled:opacity-50 disabled:cursor-not-allowed ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {isLoading && (
        <svg
          className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {!isLoading && leftIcon && <span className="inline-flex">{leftIcon}</span>}
      <span>{children}</span>
      {!isLoading && rightIcon && <span className="inline-flex">{rightIcon}</span>}
    </button>
  );
};
