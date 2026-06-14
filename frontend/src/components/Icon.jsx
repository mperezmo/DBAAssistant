// Iconos de línea (mid-century), portados 1:1 del diseño.
const PATHS = {
  home: 'M3 11 L10 4 L17 11 M5 9 V17 H15 V9',
  chat: 'M3 4 H17 V13 H10 L6 17 V13 H3 Z',
  monitor: 'M2 10 L5 10 L7 4 L11 16 L13 8 L15 10 L18 10',
  bell: 'M5 14 V9 A5 5 0 0 1 15 9 V14 L17 16 H3 Z M8 18 H12',
  play: 'M6 4 L16 10 L6 16 Z',
  sandbox: 'M4 4 H16 V16 H4 Z M4 8 H16 M8 4 V16 M12 4 V16',
  book: 'M3 4 H10 A2 2 0 0 1 12 6 V17 A1.5 1.5 0 0 0 13.5 15.5 H17 V4 M3 4 V17 H10',
  history: 'M10 4 A6 6 0 1 1 4 10 M4 4 V8 H8 M10 7 V10 L13 12',
  audit: 'M4 3 H14 L17 6 V17 H4 Z M7 9 H14 M7 12 H14 M7 15 H11',
  users: 'M7 8 A2.5 2.5 0 1 0 7 3 A2.5 2.5 0 0 0 7 8 Z M2 17 V15 A4 4 0 0 1 6 11 H8 A4 4 0 0 1 12 15 V17 M14 8 A2 2 0 1 0 14 4 M13 11 H14 A4 4 0 0 1 18 15 V17',
  settings: 'M10 7 A3 3 0 1 0 10 13 A3 3 0 0 0 10 7 Z M10 2 V4 M10 16 V18 M2 10 H4 M16 10 H18 M4.2 4.2 L5.6 5.6 M14.4 14.4 L15.8 15.8 M4.2 15.8 L5.6 14.4 M14.4 5.6 L15.8 4.2',
  search: 'M9 3 A6 6 0 1 1 9 15 A6 6 0 0 1 9 3 Z M14 14 L17 17',
  plus: 'M10 4 V16 M4 10 H16',
  arrow: 'M4 10 H16 M11 5 L16 10 L11 15',
  check: 'M4 10 L8 14 L16 5',
  x: 'M5 5 L15 15 M15 5 L5 15',
  chevron: 'M7 5 L12 10 L7 15',
  down: 'M5 7 L10 12 L15 7',
  info: 'M10 2 A8 8 0 1 0 10 18 A8 8 0 0 0 10 2 Z M10 6 V6.1 M10 9 V14',
  warn: 'M10 2 L18 17 H2 Z M10 8 V12 M10 14 V14.1',
  flask: 'M8 3 V9 L4 17 H16 L12 9 V3 M7 3 H13',
  db: 'M4 5 C4 3 6 2 10 2 C14 2 16 3 16 5 V15 C16 17 14 18 10 18 C6 18 4 17 4 15 Z M4 5 C4 7 6 8 10 8 C14 8 16 7 16 5 M4 10 C4 12 6 13 10 13 C14 13 16 12 16 10',
  table: 'M2 4 H18 V16 H2 Z M2 8 H18 M2 12 H18 M7 4 V16 M13 4 V16',
  shield: 'M10 2 L17 5 V10 C17 14 14 17 10 18 C6 17 3 14 3 10 V5 Z',
  mobile: 'M6 2 H14 V18 H6 Z M9 16 H11',
  code: 'M7 5 L2 10 L7 15 M13 5 L18 10 L13 15',
  refresh: 'M3 10 A7 7 0 0 1 14 5 L17 8 M17 4 V8 H13 M17 10 A7 7 0 0 1 6 15 L3 12 M3 16 V12 H7',
  download: 'M10 3 V13 M5 9 L10 14 L15 9 M3 17 H17',
  eye: 'M2 10 C5 5 10 3 10 3 C10 3 15 5 18 10 C15 15 10 17 10 17 C10 17 5 15 2 10 Z M10 7 A3 3 0 1 1 10 13 A3 3 0 0 1 10 7 Z',
  cpu: 'M5 5 H15 V15 H5 Z M8 5 V2 M12 5 V2 M8 18 V15 M12 18 V15 M5 8 H2 M5 12 H2 M18 8 H15 M18 12 H15',
};

export default function Icon({ name, size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" stroke="currentColor"
      strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
      <path d={PATHS[name] || PATHS.info} />
    </svg>
  );
}
