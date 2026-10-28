"use client";

import React from "react";
import { CheckCircle2, AlertTriangle, AlertCircle, Clock, XCircle } from "lucide-react";

export type BadgeVariant = "success" | "warning" | "error" | "info" | "neutral";

interface Props {
  variant: BadgeVariant;
  label: string;
  icon?: React.ReactNode;
  size?: "sm" | "md";
}

export default function StatusBadge({ variant, label, icon, size = "md" }: Props) {
  const styles: Record<BadgeVariant, { bg: string; text: string; border: string; defaultIcon: React.ReactNode }> = {
    success: {
      bg: "bg-emerald-50",
      text: "text-emerald-800",
      border: "border-emerald-300",
      defaultIcon: <CheckCircle2 className="w-4 h-4 text-emerald-700" aria-hidden="true" />,
    },
    warning: {
      bg: "bg-amber-50",
      text: "text-amber-900",
      border: "border-amber-300",
      defaultIcon: <AlertTriangle className="w-4 h-4 text-amber-700" aria-hidden="true" />,
    },
    error: {
      bg: "bg-red-50",
      text: "text-red-900",
      border: "border-red-300",
      defaultIcon: <XCircle className="w-4 h-4 text-red-700" aria-hidden="true" />,
    },
    info: {
      bg: "bg-blue-50",
      text: "text-blue-900",
      border: "border-blue-300",
      defaultIcon: <AlertCircle className="w-4 h-4 text-blue-700" aria-hidden="true" />,
    },
    neutral: {
      bg: "bg-slate-100",
      text: "text-slate-800",
      border: "border-slate-300",
      defaultIcon: <Clock className="w-4 h-4 text-slate-600" aria-hidden="true" />,
    },
  };

  const selected = styles[variant] || styles.neutral;
  const padding = size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm";

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-full border ${selected.bg} ${selected.text} ${selected.border} ${padding}`}
    >
      {icon ?? selected.defaultIcon}
      <span>{label}</span>
    </span>
  );
}
