// Gauge semicircular (mid-century) portado del diseño. value puede ser null → "—".
export default function Gauge({ label, value, unit, max = 100, warn = 70, crit = 85 }) {
  const hasValue = value != null && !Number.isNaN(value);
  const v = hasValue ? value : 0;
  const pct = Math.min(v / max, 1);
  const angle = -90 + pct * 180;
  const color = !hasValue ? 'var(--fg-faint)'
    : v >= crit ? 'var(--terracotta)'
    : v >= warn ? 'var(--mustard)'
    : 'var(--sage)';

  const cx = 100, cy = 100, r = 72;
  const arc = (start, end) => {
    const s = (start * Math.PI) / 180;
    const e = (end * Math.PI) / 180;
    return `M${cx + r * Math.cos(s)},${cy + r * Math.sin(s)} A${r},${r} 0 0,1 ${cx + r * Math.cos(e)},${cy + r * Math.sin(e)}`;
  };

  const ticks = [];
  for (let i = 0; i <= 10; i++) {
    const t = -180 + (i / 10) * 180;
    const tr = (t * Math.PI) / 180;
    const inner = i % 5 === 0 ? r - 12 : r - 6;
    ticks.push({
      x1: cx + inner * Math.cos(tr), y1: cy + inner * Math.sin(tr),
      x2: cx + r * Math.cos(tr), y2: cy + r * Math.sin(tr),
      major: i % 5 === 0,
    });
  }

  const needleAngle = (angle * Math.PI) / 180;
  const nx = cx + (r - 18) * Math.cos(needleAngle);
  const ny = cy + (r - 18) * Math.sin(needleAngle);

  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--fg-faint)', marginBottom: 6 }}>
        {label}
      </div>
      <svg viewBox="0 0 200 120" style={{ width: '100%', maxWidth: 200, height: 'auto' }}>
        <path d={arc(-180, 0)} stroke="var(--line)" strokeWidth="14" fill="none" />
        <path d={arc(-180 + (warn / max) * 180, -180 + (crit / max) * 180)} stroke="var(--mustard-bg)" strokeWidth="14" fill="none" />
        <path d={arc(-180 + (crit / max) * 180, 0)} stroke="var(--terracotta-bg)" strokeWidth="14" fill="none" />
        {hasValue && <path d={arc(-180, -180 + pct * 180)} stroke={color} strokeWidth="14" fill="none" />}
        {ticks.map((t, i) => (
          <line key={i} x1={t.x1} y1={t.y1} x2={t.x2} y2={t.y2} stroke="var(--ink-700)" strokeWidth={t.major ? 1.4 : 0.7} opacity={t.major ? 0.8 : 0.4} />
        ))}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke="var(--ink-900)" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="6" fill="var(--ink-900)" stroke="var(--bg-elev)" strokeWidth="1" />
        <circle cx={cx} cy={cy} r="2" fill="var(--bg-elev)" />
      </svg>
      <div style={{ marginTop: -10 }}>
        <div className="metric-large" style={{ fontSize: 34, color }}>
          {hasValue ? value : '—'}
          {hasValue && <span style={{ fontSize: 14, color: 'var(--fg-muted)', marginLeft: 2 }}>{unit}</span>}
        </div>
      </div>
    </div>
  );
}
