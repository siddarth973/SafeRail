import React from 'react';

interface MiniSparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
}

export const MiniSparkline: React.FC<MiniSparklineProps> = ({
  data = [65, 78, 70, 85, 92, 98],
  width = 54,
  height = 20,
  color = "#06b6d4"
}) => {
  if (!data || data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data
    .map((val, idx) => {
      const x = (idx / (data.length - 1)) * (width - 4) + 2;
      const y = height - 3 - ((val - min) / range) * (height - 6);
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
        style={{ filter: 'drop-shadow(0 0 2px rgba(6, 182, 212, 0.4))' }}
      />
    </svg>
  );
};
