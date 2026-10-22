import React from 'react';

interface CircularHealthGaugeProps {
  score: number;
  total?: number;
  statusText?: string;
  subtext?: string;
}

export const CircularHealthGauge: React.FC<CircularHealthGaugeProps> = ({
  score = 82,
  total = 100,
  statusText = "Good",
  subtext = "System is performing well."
}) => {
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / total) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-2">
      <div className="relative flex items-center justify-center w-28 h-28">
        <svg className="w-28 h-28 -rotate-90">
          {/* Background circle */}
          <circle
            cx="56"
            cy="56"
            r={radius}
            stroke="#19253d"
            strokeWidth="7"
            fill="transparent"
          />
          {/* Progress circle */}
          <circle
            cx="56"
            cy="56"
            r={radius}
            stroke="url(#oversightGlow)"
            strokeWidth="7"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-700 ease-out"
          />
          <defs>
            <linearGradient id="oversightGlow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#06b6d4" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
          </defs>
        </svg>

        {/* Text inside circle */}
        <div className="absolute flex flex-col items-center justify-center text-center">
          <div className="flex items-baseline gap-0.5">
            <span className="text-2xl font-bold text-white">{score}</span>
            <span className="text-[11px] text-slate-400">/{total}</span>
          </div>
          <span className="text-xs font-semibold text-emerald-400 mt-0.5">{statusText}</span>
        </div>
      </div>
      <p className="text-[11px] text-slate-400 mt-1 text-center">{subtext}</p>
    </div>
  );
};
