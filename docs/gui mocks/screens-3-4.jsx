/* global React */
const T3 = window.EPMC_TOKENS;
const {
  AppShell, Stepper, Card, SectionLabel, TextInput, Button,
  Check, X, ArrowLeft, ArrowRight, Folder, FolderOpen,
  Download: DownloadIcon, Plus, ExcelIcon, PdfIcon,
} = window;

/* -------------------------------------------------------------------------- */
/*  Screen 3 — Download                                                        */
/* -------------------------------------------------------------------------- */

function StatusDot({ kind }) {
  // kind: "done" | "error" | "pending"
  const dim = 26;
  if (kind === "done") {
    return (
      <div style={{
        width: dim, height: dim, borderRadius: dim/2,
        background: T3.successDeep, color: T3.success,
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
      }}>
        <Check size={14} color={T3.success} strokeWidth={2.5} />
      </div>
    );
  }
  if (kind === "error") {
    return (
      <div style={{
        width: dim, height: dim, borderRadius: dim/2,
        background: T3.dangerDeep, color: T3.danger,
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
      }}>
        <X size={12} color={T3.danger} strokeWidth={2.5} />
      </div>
    );
  }
  return (
    <div style={{
      width: dim, height: dim, borderRadius: dim/2,
      background: "rgba(255,122,61,0.10)", color: T3.accent,
      display: "flex", alignItems: "center", justifyContent: "center",
      flexShrink: 0,
    }}>
      <DownloadIcon size={13} color={T3.accent} />
    </div>
  );
}

const DOWNLOAD_ROWS = [
  { kind: "done",    file: "10.1016_j.smrv.2023.01.002_cognitive-effects-sleep-deprivation.pdf",      sub: "Saved · 1.2 MB" },
  { kind: "done",    file: "10.1523_jneurosci.1234-23_memory-reactivation-nrem-sleep.pdf",            sub: "Saved · 2.4 MB" },
  { kind: "error",   file: "10.1093_brain_awad112_hippocampal-replay-consolidation.pdf",              sub: "PDF unavailable" },
  { kind: "done",    file: "10.1016_j.neuropsychologia.2023.04.011_working-memory-sleep-architecture.pdf", sub: "Saved · 890 KB" },
  { kind: "pending", file: "10.1016_j.cub.2024.03.041_slow-wave-sleep-synaptic-homeostasis.pdf",     sub: "Thread 1 · 340 KB / 1.8 MB" },
  { kind: "pending", file: "10.1038_s41593-024-01589-z_memory-interference-sleep-consolidation.pdf",  sub: "Thread 2 · 120 KB / 2.1 MB" },
  { kind: "pending", file: "10.1523_jneurosci.0891-24_prefrontal-cortex-sleep-working-memory.pdf",   sub: "Thread 3 · 780 KB / 3.2 MB" },
];

function DownloadRow({ row, last }) {
  const subColor = row.kind === "error" ? T3.danger : T3.textMuted;
  return (
    <div style={{
      display: "flex", gap: 16, alignItems: "flex-start",
      padding: "14px 0",
      borderBottom: last ? "none" : `1px solid ${T3.divider}`,
    }}>
      <StatusDot kind={row.kind} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: T3.textPrimary, fontFamily: T3.fontMono, letterSpacing: -0.2 }}>
          {row.file}
        </div>
        <div style={{ marginTop: 4, fontSize: 14, color: subColor }}>{row.sub}</div>
      </div>
    </div>
  );
}

function DownloadScreen() {
  return (
    <AppShell width={1080} height={1180}>
      <Stepper active={2} />

      <Card style={{ padding: 26 }}>
        <SectionLabel>Download progress</SectionLabel>

        {/* Progress bar */}
        <div style={{ marginTop: 22, height: 10, background: "rgba(255,255,255,0.06)", borderRadius: 5, overflow: "hidden" }}>
          <div style={{
            height: "100%", width: "46%",
            background: T3.accent,
            borderRadius: 5,
          }}></div>
        </div>

        {/* Stats below */}
        <div style={{ marginTop: 18, display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
              <span style={{ fontSize: 22, fontWeight: 700, color: T3.accent }}>46%</span>
              <span style={{ fontSize: 18, color: T3.textPrimary }}>23 of 50 downloaded</span>
            </div>
            <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ display: "inline-flex", gap: 5 }}>
                {[0,1,2].map(i => (
                  <span key={i} style={{ width: 6, height: 6, borderRadius: 3, background: T3.accent, opacity: 0.85 - i*0.18 }}></span>
                ))}
              </span>
              <span style={{ fontSize: 14, color: T3.textMuted }}>3 threads running</span>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 26, fontWeight: 700, color: T3.textPrimary }}>~4 min</div>
            <div style={{ marginTop: 4, fontSize: 13, color: T3.textMuted }}>remaining</div>
          </div>
        </div>
      </Card>

      <Card style={{ padding: 22 }}>
        <SectionLabel>Live status</SectionLabel>
        <div style={{ marginTop: 6 }}>
          {DOWNLOAD_ROWS.map((row, i) => (
            <DownloadRow key={i} row={row} last={i === DOWNLOAD_ROWS.length - 1} />
          ))}
        </div>
      </Card>

      <div style={{ flex: 1 }}></div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, color: T3.textBody, fontSize: 15 }}>
          <Folder color={T3.textMuted} />
          <span>Saving to /Users/researcher/papers</span>
        </div>
        <Button variant="secondary">
          <X color={T3.textPrimary} /> Cancel
        </Button>
      </div>
    </AppShell>
  );
}

/* -------------------------------------------------------------------------- */
/*  Screen 4 — Summary                                                         */
/* -------------------------------------------------------------------------- */

function SummaryStat({ label, value, sub, valueColor = T3.textPrimary }) {
  return (
    <Card style={{ padding: 22 }}>
      <div style={{ fontSize: 15, color: T3.textBody, fontWeight: 500 }}>{label}</div>
      <div style={{ marginTop: 10, fontSize: 44, fontWeight: 600, color: valueColor, lineHeight: 1 }}>{value}</div>
      <div style={{ marginTop: 12, fontSize: 13, color: T3.textMuted }}>{sub}</div>
    </Card>
  );
}

function ParamPair({ label, value }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 16, color: T3.textMuted }}>{label}</span>
      <span style={{ fontSize: 16, color: T3.textPrimary, fontWeight: 600 }}>{value}</span>
    </span>
  );
}

const SKIPPED_PAPERS = [
  { title: "Hippocampal replay and memory consolidation during sleep",
    meta: "Brown A, Clarke M, Patel R · Brain · 2023",
    reason: "PDF unavailable" },
  { title: "Working memory and slow-wave sleep in ageing populations",
    meta: "Martinez C, Fischer H · Neuropsychologia · 2023",
    reason: "Already downloaded" },
];

function SkippedRow({ paper, last }) {
  return (
    <div style={{
      display: "flex", gap: 16, alignItems: "flex-start",
      padding: "16px 0",
      borderBottom: last ? "none" : `1px solid ${T3.divider}`,
    }}>
      <div style={{
        width: 26, height: 26, borderRadius: 13,
        background: T3.dangerDeep, color: T3.danger, flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
      }}>
        <X size={12} color={T3.danger} strokeWidth={2.5} />
      </div>
      <div>
        <div style={{ fontSize: 18, fontWeight: 600, color: T3.textPrimary }}>{paper.title}</div>
        <div style={{ marginTop: 6, fontSize: 14, color: T3.textMuted }}>{paper.meta}</div>
        <div style={{ marginTop: 6, fontSize: 14, color: T3.danger, fontWeight: 500 }}>{paper.reason}</div>
      </div>
    </div>
  );
}

function SummaryScreen() {
  return (
    <AppShell width={1080} height={1080}>
      <Stepper active={3} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <SummaryStat label="Downloaded" value="48" sub="of 50 requested" valueColor={T3.success} />
        <SummaryStat label="Skipped" value="2" sub="see reasons below" valueColor={T3.danger} />
        <SummaryStat label="Total results" value="1,247" sub="found in Europe PMC" />
      </div>

      <Card style={{ padding: 22 }}>
        <SectionLabel>Search parameters</SectionLabel>
        <div style={{ marginTop: 18, display: "flex", flexWrap: "wrap", columnGap: 36, rowGap: 14 }}>
          <ParamPair label="Query" value="memory AND sleep OR cognition" />
          <ParamPair label="Sort" value="Relevance" />
          <ParamPair label="Date" value="2021-05-07 → 2026-05-07" />
          <ParamPair label="License" value="CC-BY" />
          <ParamPair label="Publication types" value="9 selected" />
          <ParamPair label="Authors" value="2 ORCIDs" />
        </div>
      </Card>

      <Card style={{ padding: 22 }}>
        <SectionLabel>Skipped papers</SectionLabel>
        <div style={{ marginTop: 8 }}>
          {SKIPPED_PAPERS.map((p, i) => (
            <SkippedRow key={p.title} paper={p} last={i === SKIPPED_PAPERS.length - 1} />
          ))}
        </div>
      </Card>

      <div style={{ flex: 1 }}></div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 6 }}>
        <Button variant="secondary">
          <Plus size={16} color={T3.textPrimary} /> New search
        </Button>
        <div style={{ display: "flex", gap: 12 }}>
          <Button variant="secondary">
            <ExcelIcon color={T3.textPrimary} /> Export Excel
          </Button>
          <Button variant="secondary">
            <PdfIcon color={T3.textPrimary} /> Export PDF
          </Button>
        </div>
      </div>
    </AppShell>
  );
}

Object.assign(window, { DownloadScreen, SummaryScreen, StatusDot, DownloadRow, SkippedRow });
