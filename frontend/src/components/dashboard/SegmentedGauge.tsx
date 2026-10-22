import React from 'react';

interface SegmentedGaugeProps {
  value: number; // e.g. 98
  totalSegments?: number;
  className?: string;
}

export const SegmentedGauge: React.FC<SegmentedGaugeProps> = ({
  value,
  totalSegments = 28,
  className = ""
}) => {
  const activeSegments = Math.round((value / 100) * totalSegments);
  const segments = [];
  
  const radius = 80;
  const startAngle = 180; // left
  const endAngle = 360;   // right
  const angleStep = (endAngle - startAngle) / (totalSegments - 1);

  for (let i = 0; i < totalSegments; i++) {
    const angle = startAngle + i * angleStep;
    const rad = (angle * Math.PI) / 180;
    
    // Ticks positioned along arc
    const x1 = 110 + (radius - 12) * Math.cos(rad);
    const y1 = 115 + (radius - 12) * Math.sin(rad);
    const x2 = 110 + (radius + 4) * Math.cos(rad);
    const y2 = 115 + (radius + 4) * Math.sin(rad);

    const isActive = i < activeSegments;
    
    // Color gradient calculation
    const progress = i / totalSegments;
    const strokeColor = isActive
      ? progress > 0.85
        ? '#10b981' // emerald
        : '#06b6d4' // cyan
      : '#1e293b';  // inactive dark slate

    segments.push(
      <line
        key={i}
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={strokeColor}
        strokeWidth="4.5"
        strokeLinecap="round"
        className="transition-all duration-300"
        style={{
          filter: isActive ? 'drop-shadow(0 0 3px rgba(6, 182, 212, 0.6))' : 'none'
        }}
      />
    );
  }

  return (
    <div className={`relative flex flex-col items-center justify-center ${className}`}>
      <svg viewBox="0 0 220 135" className="w-56 h-36 overflow-visible">
        <defs>
          <linearGradient id="gaugeGlow" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>
        </defs>
        {segments}
      </svg>
      {/* Centered value */}
      <div className="absolute top-[52px] flex flex-col items-center">
        <span className="text-3xl font-bold tracking-tight text-white drop-shadow-sm">
          {value}%
        </span>
        <span className="text-sm font-medium text-emerald-400 -mt-0.5">
          Healthy
        </span>
      </div>
    </div>
  );
};
