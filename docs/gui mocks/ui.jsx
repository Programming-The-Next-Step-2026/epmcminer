/* global React */

// Design tokens — single source of truth for all screens.
// Mirrors what you'd put into a PyQt6 stylesheet.
window.EPMC_TOKENS = {
  // surfaces
  appBg:       "#0b0b0d",
  windowBg:    "#141416",
  cardBg:      "#1c1c1f",
  cardInner:   "#242427",
  divider:     "rgba(255,255,255,0.06)",
  border:      "rgba(255,255,255,0.07)",

  // text
  textPrimary: "#ededed",
  textBody:    "#cfcfcf",
  textMuted:   "#8a8a8d",
  textFaint:   "#6a6a6d",

  // brand / accents
  accent:      "#ff7a3d",     // primary orange
  accentSoft:  "#ff9a6a",     // lighter for chip text
  accentDeep:  "#3a2218",     // chip background
  accentDeepBorder: "#5a3424",

  success:     "#7bc77b",
  successDeep: "#1f3a23",
  danger:      "#ff8a85",
  dangerDeep:  "#3a1f1f",

  // type
  fontStack:   "'Inter', 'SF Pro Text', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
  fontMono:    "'JetBrains Mono', 'SF Mono', Menlo, monospace",

  // radii
  radiusCard:    16,
  radiusInput:   12,
  radiusButton:  12,
  radiusChip:    9999,

  // spacing scale (4pt base)
  s1: 4, s2: 8, s3: 12, s4: 16, s5: 20, s6: 24, s7: 32, s8: 40,
};

const T = window.EPMC_TOKENS;

/* -------------------------------------------------------------------------- */
/*  App shell — emulates the macOS-ish window from the screenshots            */
/* -------------------------------------------------------------------------- */

function AppShell({ children, width = 1080, height = 900, showTrafficLights = true, showMenuDots = false }) {
  return (
    <div
      style={{
        width, height,
        background: T.windowBg,
        borderRadius: 14,
        border: `1px solid ${T.border}`,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        fontFamily: T.fontStack,
        color: T.textPrimary,
        boxShadow: "0 30px 80px rgba(0,0,0,0.45)",
      }}
    >
      <TitleBar showTrafficLights={showTrafficLights} showMenuDots={showMenuDots} />
      <div style={{ flex: 1, background: T.appBg, padding: 22, display: "flex", flexDirection: "column", gap: 18, overflow: "hidden" }}>
        {children}
      </div>
    </div>
  );
}

function TitleBar({ showTrafficLights, showMenuDots }) {
  return (
    <div style={{
      height: 44,
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 18px",
      borderBottom: `1px solid ${T.border}`,
      background: T.windowBg,
      position: "relative",
    }}>
      <div style={{ display: "flex", gap: 8 }}>
        {showTrafficLights && (
          <>
            <span style={{ width: 12, height: 12, borderRadius: 6, background: "#ff5f57" }}></span>
            <span style={{ width: 12, height: 12, borderRadius: 6, background: "#febc2e" }}></span>
            <span style={{ width: 12, height: 12, borderRadius: 6, background: "#28c840" }}></span>
          </>
        )}
      </div>
      <div style={{
        position: "absolute", left: 0, right: 0, textAlign: "center",
        fontSize: 12, letterSpacing: 1.3, color: T.textMuted, fontWeight: 500,
      }}>EPMCMINER</div>
      <div style={{ width: 60, textAlign: "right", color: T.textMuted, fontSize: 18, letterSpacing: 1 }}>
        {showMenuDots ? "···" : ""}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Step indicator                                                             */
/* -------------------------------------------------------------------------- */

const STEPS = ["Search", "Preview", "Download", "Summary"];

function Stepper({ active }) {
  // active: 0..3 — completed steps come before
  return (
    <div style={{ display: "flex", alignItems: "center", padding: "8px 4px 18px", borderBottom: `1px solid ${T.border}` }}>
      {STEPS.map((label, i) => {
        const isActive = i === active;
        const isDone = i < active;
        return (
          <React.Fragment key={label}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 28, height: 28, borderRadius: 14,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: isActive ? T.accent : "transparent",
                border: isActive ? "none" : `1.5px solid ${isDone ? T.textMuted : "rgba(255,255,255,0.15)"}`,
                color: isActive ? "#1a0e07" : isDone ? T.textMuted : T.textMuted,
                fontWeight: 600, fontSize: 13,
              }}>
                {isDone ? <Check size={14} color={T.textMuted} /> : (i + 1)}
              </div>
              <div style={{
                fontSize: 17, fontWeight: 500,
                color: isActive ? T.accent : isDone ? T.textPrimary : T.textMuted,
              }}>{label}</div>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)", margin: "0 18px" }}></div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Card + Section header                                                      */
/* -------------------------------------------------------------------------- */

function Card({ children, style, padding = 22 }) {
  return (
    <div style={{
      background: T.cardBg,
      borderRadius: T.radiusCard,
      border: `1px solid ${T.border}`,
      padding,
      ...style,
    }}>
      {children}
    </div>
  );
}

function SectionLabel({ children, style }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, ...style }}>
      <span style={{ width: 3, height: 14, borderRadius: 2, background: T.accent }}></span>
      <span style={{
        fontSize: 11, letterSpacing: 1.6, fontWeight: 600,
        color: T.textPrimary, textTransform: "uppercase",
      }}>{children}</span>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Inputs                                                                     */
/* -------------------------------------------------------------------------- */

function TextInput({ value, placeholder, monoLike, style }) {
  return (
    <div style={{
      background: T.cardInner,
      border: `1px solid ${T.border}`,
      borderRadius: T.radiusInput,
      padding: "14px 16px",
      fontSize: monoLike ? 18 : 18,
      color: value ? T.textPrimary : T.textFaint,
      fontWeight: 400,
      ...style,
    }}>
      {value || placeholder}
    </div>
  );
}

function Chip({ children, removable = true, variant = "accent" }) {
  const isAccent = variant === "accent";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 8,
      padding: "6px 12px",
      borderRadius: T.radiusChip,
      background: isAccent ? T.accentDeep : "transparent",
      border: `1px solid ${isAccent ? T.accentDeepBorder : "rgba(255,255,255,0.18)"}`,
      color: isAccent ? T.accentSoft : T.textPrimary,
      fontSize: 14, fontWeight: 500,
      whiteSpace: "nowrap",
    }}>
      {children}
      {removable && (
        <span style={{ color: isAccent ? T.accentSoft : T.textMuted, opacity: 0.75, fontSize: 14 }}>×</span>
      )}
    </span>
  );
}

function AddChip({ children = "Add" }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "8px 14px",
      borderRadius: T.radiusChip,
      background: "transparent",
      border: `1px solid rgba(255,255,255,0.18)`,
      color: T.textPrimary,
      fontSize: 14, fontWeight: 500,
    }}>
      <span style={{ fontSize: 16, lineHeight: 1, color: T.textPrimary }}>+</span> {children}
    </span>
  );
}

function Button({ children, variant = "secondary", style, icon }) {
  const palette = {
    primary:   { bg: T.accent, color: "#1a0e07", border: "transparent" },
    secondary: { bg: "transparent", color: T.textPrimary, border: "rgba(255,255,255,0.16)" },
    ghost:     { bg: "transparent", color: T.textPrimary, border: "transparent" },
  }[variant];

  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 10,
      padding: "12px 22px",
      borderRadius: T.radiusButton,
      background: palette.bg,
      color: palette.color,
      border: `1px solid ${palette.border}`,
      fontSize: 17, fontWeight: 500,
      cursor: "default",
      ...style,
    }}>
      {icon}
      {children}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  Tiny icons (inline SVG — avoids font deps)                                 */
/* -------------------------------------------------------------------------- */

function Check({ size = 14, color = "currentColor", strokeWidth = 2.2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M5 12.5l4.5 4.5L19 7.5" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function X({ size = 14, color = "currentColor", strokeWidth = 2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M6 6l12 12M18 6L6 18" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
    </svg>
  );
}

function ArrowRight({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M5 12h14M13 6l6 6-6 6" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ArrowLeft({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M19 12H5M11 6l-6 6 6 6" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ArrowDown({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M6 13l6 6 6-6" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Lock({ size = 14, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="5" y="11" width="14" height="9" rx="2" stroke={color} strokeWidth={1.8} />
      <path d="M8 11V7.5a4 4 0 018 0V11" stroke={color} strokeWidth={1.8} strokeLinecap="round" />
    </svg>
  );
}

function Folder({ size = 16, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V7z" stroke={color} strokeWidth={1.6} />
    </svg>
  );
}

function FolderOpen({ size = 16, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v0H3z" stroke={color} strokeWidth={1.6} strokeLinejoin="round" />
      <path d="M3 9h18l-2.4 8.4A2 2 0 0116.7 19H5.3a2 2 0 01-1.95-1.56L3 9z" stroke={color} strokeWidth={1.6} strokeLinejoin="round" />
    </svg>
  );
}

function Download({ size = 16, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 4v12M6 12l6 6 6-6M5 20h14" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Plus({ size = 16, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke={color} strokeWidth={2} strokeLinecap="round" />
    </svg>
  );
}

function ChevronDown({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M6 9l6 6 6-6" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ExcelIcon({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="3" y="4" width="18" height="16" rx="2" stroke={color} strokeWidth={1.6} />
      <path d="M3 10h18M3 16h18M9 4v16M15 4v16" stroke={color} strokeWidth={1.4} />
    </svg>
  );
}

function PdfIcon({ size = 18, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M7 3h8l4 4v14a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z" stroke={color} strokeWidth={1.6} strokeLinejoin="round" />
      <path d="M15 3v4h4" stroke={color} strokeWidth={1.6} strokeLinejoin="round" />
      <text x="9" y="17" fontSize="5.5" fontWeight="700" fill={color} fontFamily="monospace">PDF</text>
    </svg>
  );
}

// Expose to global scope so other JSX scripts can pick them up
Object.assign(window, {
  AppShell, TitleBar, Stepper, Card, SectionLabel,
  TextInput, Chip, AddChip, Button,
  Check, X, ArrowRight, ArrowLeft, ArrowDown, Lock, Folder, FolderOpen, Download, Plus, ChevronDown, ExcelIcon, PdfIcon,
  STEPS,
});
