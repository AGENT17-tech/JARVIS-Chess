import React, { useEffect, useState } from 'react';
import useTheme from '../hooks/useTheme';

const DESCRIPTIONS = [
  [5, 'Weakest'],
  [10, 'Balanced'],
  [15, 'Strong'],
  [20, 'Strongest (slow)'],
];

function describe(depth) {
  const found = DESCRIPTIONS.find(([max]) => depth <= max);
  return found ? found[1] : DESCRIPTIONS[DESCRIPTIONS.length - 1][1];
}

// Sends "set_depth" over the game's WebSocket (see api_server.py's
// websocket_endpoint and GameEngine.set_depth) — takes effect on JARVIS's
// next move, persists until changed again. `onChange` only fires once the
// slider is released, not on every tick while dragging.
export default function EngineDepthControl({ depth, onChange, disabled }) {
  const { colors } = useTheme();
  const [localDepth, setLocalDepth] = useState(depth);

  useEffect(() => setLocalDepth(depth), [depth]);

  return (
    <div
      style={{
        display: 'flex', alignItems: 'center', gap: '12px', backgroundColor: colors.panelBg,
        border: `1px solid ${colors.border}`, borderRadius: '8px', padding: '8px 16px', fontSize: '13px',
      }}
      role="group"
      aria-label="Engine depth control"
    >
      <label htmlFor="engine-depth" style={{ color: colors.text, fontWeight: 'bold', whiteSpace: 'nowrap' }}>
        Engine Depth: {localDepth}
      </label>
      <input
        id="engine-depth"
        type="range"
        min="1"
        max="20"
        value={localDepth}
        disabled={disabled}
        onChange={(e) => setLocalDepth(Number(e.target.value))}
        onMouseUp={(e) => onChange(Number(e.target.value))}
        onTouchEnd={(e) => onChange(Number(e.target.value))}
        onKeyUp={(e) => onChange(Number(e.target.value))}
        style={{ width: '160px' }}
        aria-valuetext={`Depth ${localDepth}, ${describe(localDepth)}`}
      />
      <span style={{ color: colors.textSecondary, fontSize: '11px', minWidth: '110px' }}>{describe(localDepth)}</span>
    </div>
  );
}
