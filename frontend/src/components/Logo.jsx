export default function Logo({ size = 40, mono = false, color }) {
  const c1 = mono ? (color || 'currentColor') : '#1E4FBF';
  const c2 = mono ? (color || 'currentColor') : '#0A2F8F';
  const c3 = mono ? (color || 'currentColor') : '#94B8FF';
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" style={{ flexShrink: 0 }}>
      {/* Head — hexagonal */}
      <path d="M32 6 L48 14 L48 26 L32 34 L16 26 L16 14 Z" fill={c1} />
      <path d="M32 6 L32 34 L48 26 L48 14 Z" fill={c2} />
      {/* Eyes */}
      <circle cx="26" cy="20" r="3" fill={c3} />
      <circle cx="38" cy="20" r="3" fill={c3} />
      {/* Neck */}
      <rect x="28" y="32" width="8" height="4" fill={c1} />
      {/* Database body — three discs */}
      <rect x="14" y="38" width="36" height="6" fill={c1} />
      <rect x="32" y="38" width="18" height="6" fill={c2} />
      <rect x="14" y="46" width="36" height="6" fill={c1} />
      <rect x="32" y="46" width="18" height="6" fill={c2} />
      <rect x="14" y="54" width="36" height="6" fill={c1} />
      <rect x="32" y="54" width="18" height="6" fill={c2} />
    </svg>
  );
}
