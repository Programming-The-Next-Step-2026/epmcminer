/* global React */
const TH = window.EPMC_TOKENS;

/* -------------------------------------------------------------------------- */
/*  Tokens card — single visual reference for hex / spacing / type             */
/* -------------------------------------------------------------------------- */

function TokenSwatch({ name, value, label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "10px 0", borderBottom: `1px solid ${TH.divider}` }}>
      <div style={{ width: 44, height: 44, borderRadius: 10, background: value, border: `1px solid ${TH.border}`, flexShrink: 0 }}></div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: TH.textPrimary }}>{name}</div>
        <div style={{ fontSize: 13, color: TH.textMuted }}>{label}</div>
      </div>
      <div style={{ fontFamily: TH.fontMono, fontSize: 13, color: TH.textBody }}>{value}</div>
    </div>
  );
}

function TokensScreen() {
  return (
    <div style={{
      width: 1080,
      background: TH.appBg,
      borderRadius: 14,
      border: `1px solid ${TH.border}`,
      padding: 32,
      fontFamily: TH.fontStack,
      color: TH.textPrimary,
      display: "flex",
      flexDirection: "column",
      gap: 22,
    }}>
      <div>
        <div style={{ fontSize: 13, color: TH.accent, letterSpacing: 1.6, fontWeight: 600, textTransform: "uppercase" }}>Design tokens</div>
        <div style={{ marginTop: 6, fontSize: 28, fontWeight: 600 }}>EPMCMINER — visual system</div>
        <div style={{ marginTop: 8, fontSize: 15, color: TH.textMuted, maxWidth: 760 }}>
          Lifted directly from <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>window.EPMC_TOKENS</code> in <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>ui.jsx</code>. Use these exact hex values in your PyQt6 stylesheet.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        {/* Surfaces */}
        <div style={{ background: TH.cardBg, border: `1px solid ${TH.border}`, borderRadius: 14, padding: 18 }}>
          <div style={{ fontSize: 12, letterSpacing: 1.4, fontWeight: 600, color: TH.textMuted, textTransform: "uppercase", marginBottom: 6 }}>Surfaces</div>
          <TokenSwatch name="appBg" value="#0b0b0d" label="window content background" />
          <TokenSwatch name="windowBg" value="#141416" label="title bar / outer frame" />
          <TokenSwatch name="cardBg" value="#1c1c1f" label="card background" />
          <TokenSwatch name="cardInner" value="#242427" label="input / inner field" />
        </div>

        {/* Text */}
        <div style={{ background: TH.cardBg, border: `1px solid ${TH.border}`, borderRadius: 14, padding: 18 }}>
          <div style={{ fontSize: 12, letterSpacing: 1.4, fontWeight: 600, color: TH.textMuted, textTransform: "uppercase", marginBottom: 6 }}>Text</div>
          <TokenSwatch name="textPrimary" value="#ededed" label="headings, values, primary copy" />
          <TokenSwatch name="textBody" value="#cfcfcf" label="body / authors line" />
          <TokenSwatch name="textMuted" value="#8a8a8d" label="meta, hints, captions" />
          <TokenSwatch name="textFaint" value="#6a6a6d" label="placeholders" />
        </div>

        {/* Accents */}
        <div style={{ background: TH.cardBg, border: `1px solid ${TH.border}`, borderRadius: 14, padding: 18 }}>
          <div style={{ fontSize: 12, letterSpacing: 1.4, fontWeight: 600, color: TH.textMuted, textTransform: "uppercase", marginBottom: 6 }}>Brand & state</div>
          <TokenSwatch name="accent" value="#ff7a3d" label="primary orange — step active, progress, DOIs" />
          <TokenSwatch name="accentSoft" value="#ff9a6a" label="chip text" />
          <TokenSwatch name="accentDeep" value="#3a2218" label="chip background" />
          <TokenSwatch name="success" value="#7bc77b" label="downloaded count, check icon" />
          <TokenSwatch name="successDeep" value="#1f3a23" label="check icon background" />
          <TokenSwatch name="danger" value="#ff8a85" label="skipped count, error reason" />
          <TokenSwatch name="dangerDeep" value="#3a1f1f" label="error icon background" />
        </div>

        {/* Type & geometry */}
        <div style={{ background: TH.cardBg, border: `1px solid ${TH.border}`, borderRadius: 14, padding: 18 }}>
          <div style={{ fontSize: 12, letterSpacing: 1.4, fontWeight: 600, color: TH.textMuted, textTransform: "uppercase", marginBottom: 10 }}>Type</div>
          <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", rowGap: 10, columnGap: 12, fontSize: 14, color: TH.textBody }}>
            <div style={{ color: TH.textMuted }}>Family</div><div style={{ fontFamily: TH.fontMono, fontSize: 13 }}>Inter, SF Pro Text, system-ui</div>
            <div style={{ color: TH.textMuted }}>Mono</div><div style={{ fontFamily: TH.fontMono, fontSize: 13 }}>JetBrains Mono, SF Mono, Menlo</div>
            <div style={{ color: TH.textMuted }}>Section label</div><div>11px / 600 / 1.6 tracking / uppercase</div>
            <div style={{ color: TH.textMuted }}>Body</div><div>14–15px / 400–500</div>
            <div style={{ color: TH.textMuted }}>Field</div><div>18px / 400</div>
            <div style={{ color: TH.textMuted }}>Stat value</div><div>44px / 600</div>
            <div style={{ color: TH.textMuted }}>Button</div><div>17px / 500</div>
          </div>

          <div style={{ fontSize: 12, letterSpacing: 1.4, fontWeight: 600, color: TH.textMuted, textTransform: "uppercase", marginTop: 18, marginBottom: 10 }}>Radius & spacing</div>
          <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", rowGap: 10, columnGap: 12, fontSize: 14, color: TH.textBody }}>
            <div style={{ color: TH.textMuted }}>Card</div><div>16 px</div>
            <div style={{ color: TH.textMuted }}>Input</div><div>12 px</div>
            <div style={{ color: TH.textMuted }}>Button</div><div>12 px</div>
            <div style={{ color: TH.textMuted }}>Chip</div><div>pill (fully rounded)</div>
            <div style={{ color: TH.textMuted }}>Spacing</div><div>4 / 8 / 12 / 16 / 20 / 24 / 32 / 40</div>
            <div style={{ color: TH.textMuted }}>Card padding</div><div>22 px</div>
            <div style={{ color: TH.textMuted }}>Card gap</div><div>18 px (vertical)</div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/*  PyQt6 mapping artboard                                                     */
/* -------------------------------------------------------------------------- */

const PYQT_ROWS = [
  { ui: "Window / title bar",       qt: "QMainWindow",           note: "Use native frame on macOS; central widget is the page stack." },
  { ui: "4-step navigation",        qt: "QStackedWidget",        note: "One QWidget per step. Step indicator is a separate composite of QFrame + QLabel." },
  { ui: "Step pill (number circle)",qt: "QLabel + QSS",          note: "Fixed 28×28; border-radius: 14; switch background between accent / transparent." },
  { ui: "Card",                     qt: "QFrame",                note: "objectName='card'; QSS background, border-radius: 16, padding via layout margins." },
  { ui: "Section label + bar",      qt: "QWidget (HBox)",        note: "3×14px QFrame as the orange bar + QLabel with uppercase letter-spacing." },
  { ui: "Search query input",       qt: "QLineEdit",             note: "Custom QSS — padding 14/16; font-size 18px." },
  { ui: "ORCID / type / license chip", qt: "QPushButton + QSS",  note: "Rounded pill; icon='×' on right. Emit clicked → remove from model." },
  { ui: "Add chip (+ button)",      qt: "QPushButton",           note: "Outlined variant; open small popup for input." },
  { ui: "Date range fields",        qt: "QDateEdit ×2",          note: "displayFormat='yyyy-MM-dd'; no calendar popup if you want the minimalist look — or QCalendarWidget." },
  { ui: "Sort dropdown",            qt: "QComboBox",             note: "Style chevron via QSS ::down-arrow." },
  { ui: "Open-access lock toggle",  qt: "QCheckBox or QPushButton(checkable)", note: "Render lock icon via QIcon; visible orange when active." },
  { ui: "Stat tile",                qt: "QFrame (VBox)",         note: "Three QLabels — label / value / sub. Color via setStyleSheet." },
  { ui: "Result row (preview)",     qt: "QFrame inside QScrollArea", note: "Title / authors / venue·year·DOI labels; DOI is QLabel with rich-text linkColor." },
  { ui: "Progress bar",             qt: "QProgressBar",          note: "QSS chunk { background: #ff7a3d; border-radius: 5; } height: 10." },
  { ui: "Threads dots indicator",   qt: "Custom QWidget paintEvent", note: "Three filled circles, optional pulse via QPropertyAnimation." },
  { ui: "Live status row",          qt: "QListView (delegate)",  note: "QStyledItemDelegate paints icon disc + monospace filename + sub line." },
  { ui: "Skipped paper row",        qt: "Same delegate pattern", note: "Reuse with different status enum." },
  { ui: "Primary button",           qt: "QPushButton",           note: "objectName='primary'; full orange fill, dark text." },
  { ui: "Secondary button",         qt: "QPushButton",           note: "objectName='secondary'; transparent bg, 1px white-16 border." },
  { ui: "Browse folder",            qt: "QPushButton → QFileDialog.getExistingDirectory", note: "Set initial path from settings." },
  { ui: "Export Excel / PDF",       qt: "QPushButton → QFileDialog.getSaveFileName", note: "Excel via openpyxl/xlsxwriter; PDF via QTextDocument.print() or reportlab." },
];

function PyQtScreen() {
  return (
    <div style={{
      width: 1080,
      background: TH.appBg,
      borderRadius: 14,
      border: `1px solid ${TH.border}`,
      padding: 32,
      fontFamily: TH.fontStack,
      color: TH.textPrimary,
      display: "flex",
      flexDirection: "column",
      gap: 22,
    }}>
      <div>
        <div style={{ fontSize: 13, color: TH.accent, letterSpacing: 1.6, fontWeight: 600, textTransform: "uppercase" }}>Handoff</div>
        <div style={{ marginTop: 6, fontSize: 28, fontWeight: 600 }}>PyQt6 widget mapping</div>
        <div style={{ marginTop: 8, fontSize: 15, color: TH.textMuted, maxWidth: 800 }}>
          Suggested mapping from each visual element to a Qt widget + the styling approach. PyQt6 supports a CSS-like stylesheet language — translate the design tokens above into a single global <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>setStyleSheet()</code> using object names.
        </div>
      </div>

      <div style={{ background: TH.cardBg, border: `1px solid ${TH.border}`, borderRadius: 14, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr 2fr", padding: "12px 18px", fontSize: 12, letterSpacing: 1.4, fontWeight: 600, color: TH.textMuted, textTransform: "uppercase", borderBottom: `1px solid ${TH.divider}` }}>
          <div>UI element</div>
          <div>Qt widget</div>
          <div>Notes</div>
        </div>
        {PYQT_ROWS.map((r, i) => (
          <div key={i} style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr 2fr", padding: "12px 18px", fontSize: 14, borderBottom: i === PYQT_ROWS.length - 1 ? "none" : `1px solid ${TH.divider}`, alignItems: "start" }}>
            <div style={{ color: TH.textPrimary, fontWeight: 500 }}>{r.ui}</div>
            <div style={{ color: TH.accent, fontFamily: TH.fontMono, fontSize: 13 }}>{r.qt}</div>
            <div style={{ color: TH.textBody, lineHeight: 1.5 }}>{r.note}</div>
          </div>
        ))}
      </div>

      <div style={{ background: TH.cardBg, border: `1px solid ${TH.border}`, borderRadius: 14, padding: 22 }}>
        <div style={{ fontSize: 12, letterSpacing: 1.4, fontWeight: 600, color: TH.textMuted, textTransform: "uppercase", marginBottom: 14 }}>Starter stylesheet snippet</div>
        <pre style={{
          margin: 0, padding: 18,
          background: "#0a0a0c", borderRadius: 10,
          fontFamily: TH.fontMono, fontSize: 12.5, lineHeight: 1.55,
          color: TH.textBody, overflow: "hidden", whiteSpace: "pre",
        }}>
{`QMainWindow             { background: #141416; }
QWidget#page            { background: #0b0b0d; }

QFrame#card {
    background: #1c1c1f;
    border: 1px solid rgba(255,255,255,18);
    border-radius: 16px;
}

QLabel#sectionLabel {
    color: #ededed;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.6px;
    text-transform: uppercase;
}

QLineEdit, QDateEdit, QComboBox {
    background: #242427;
    color: #ededed;
    border: 1px solid rgba(255,255,255,18);
    border-radius: 12px;
    padding: 14px 16px;
    font-size: 18px;
    selection-background-color: #ff7a3d;
}

QPushButton#chip {
    background: #3a2218;
    color: #ff9a6a;
    border: 1px solid #5a3424;
    border-radius: 14px;
    padding: 6px 12px;
    font-size: 14px;
}

QPushButton#primary {
    background: #ff7a3d;
    color: #1a0e07;
    border: none;
    border-radius: 12px;
    padding: 12px 22px;
    font-size: 17px;
    font-weight: 500;
}

QPushButton#secondary {
    background: transparent;
    color: #ededed;
    border: 1px solid rgba(255,255,255,40);
    border-radius: 12px;
    padding: 12px 22px;
}

QProgressBar {
    background: rgba(255,255,255,15);
    border: none;
    border-radius: 5px;
    height: 10px;
}
QProgressBar::chunk {
    background: #ff7a3d;
    border-radius: 5px;
}`}
        </pre>
      </div>

      <div style={{ background: TH.cardBg, border: `1px solid ${TH.border}`, borderRadius: 14, padding: 22 }}>
        <div style={{ fontSize: 12, letterSpacing: 1.4, fontWeight: 600, color: TH.textMuted, textTransform: "uppercase", marginBottom: 14 }}>Architecture suggestions</div>
        <ul style={{ margin: 0, paddingLeft: 22, fontSize: 14, lineHeight: 1.7, color: TH.textBody }}>
          <li>One <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>QStackedWidget</code> drives the 4 steps. A shared top <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>StepIndicator</code> widget reads the current index.</li>
          <li>Use a <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>QThread</code> + <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>QObject</code> worker pattern for downloads. Emit signals: <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>progressed(int)</code>, <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>fileDone(meta)</code>, <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>fileFailed(meta, reason)</code>, <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>finished()</code>.</li>
          <li>Result list = <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>QListView</code> backed by a <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>QAbstractListModel</code> + custom delegate — avoids redraw flicker on long lists.</li>
          <li>Chips are <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>QPushButton</code>s in a <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>FlowLayout</code> (Qt example layout; not built-in). Wires nicely to a backing list model.</li>
          <li>Persist the output folder + last query with <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>QSettings</code>.</li>
          <li>Icons: ship SVGs in <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>resources/icons/</code> and load via <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>QIcon(":/icons/check.svg")</code> through a <code style={{ color: TH.accent, fontFamily: TH.fontMono }}>.qrc</code>.</li>
        </ul>
      </div>
    </div>
  );
}

Object.assign(window, { TokensScreen, PyQtScreen });
