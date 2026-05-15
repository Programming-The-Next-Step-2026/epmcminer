/* global React */
const T = window.EPMC_TOKENS;
const {
  AppShell, Stepper, Card, SectionLabel, TextInput, Chip, AddChip, Button,
  Lock, ArrowRight, ArrowDown, Plus, ChevronDown,
} = window;

/* -------------------------------------------------------------------------- */
/*  Screen 1 — Search                                                          */
/* -------------------------------------------------------------------------- */

function SearchScreen() {
  return (
    <AppShell width={1080} height={1040}>
      <Stepper active={0} />

      <Card>
        <SectionLabel>Search query</SectionLabel>
        <div style={{ height: 14 }}></div>
        <TextInput value="memory AND sleep OR cognition" />
        <div style={{ marginTop: 12, fontSize: 13, color: T.textMuted }}>
          Defaults to AND if no operator specified
        </div>
      </Card>

      <Card>
        <SectionLabel>Author ORCIDs</SectionLabel>
        <div style={{ height: 14 }}></div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
          <Chip>0000-0001-5109-3700</Chip>
          <Chip>0000-0002-1825-0097</Chip>
          <AddChip>Add ORCID</AddChip>
        </div>
        <div style={{ marginTop: 14, fontSize: 13, color: T.textMuted }}>
          Multiple ORCIDs use OR logic — leave empty to search all authors
        </div>
      </Card>

      <Card>
        <SectionLabel>Publication types</SectionLabel>
        <div style={{ height: 14 }}></div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
          {["Review","Meta analysis","Clinical trial","Systematic review","Observational study","Twin study","Validation study","Case reports","Dataset"].map(t => (
            <Chip key={t}>{t}</Chip>
          ))}
          <AddChip>Add type</AddChip>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
        <Card>
          <SectionLabel>License</SectionLabel>
          <div style={{ height: 14 }}></div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
            <Chip>CC-BY</Chip>
            <AddChip>Add</AddChip>
          </div>
        </Card>

        <Card>
          <SectionLabel>Date range</SectionLabel>
          <div style={{ height: 14 }}></div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 24px 1fr", alignItems: "center", gap: 10 }}>
            <TextInput value="2021-05-07" />
            <div style={{ textAlign: "center", color: T.textMuted }}>→</div>
            <TextInput value="2026-05-07" />
          </div>
        </Card>
      </div>

      <div style={{ flex: 1 }}></div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, color: T.accent, fontSize: 15 }}>
          <Lock color={T.accent} />
          <span style={{ color: T.textBody }}>Open-access papers only</span>
        </div>
        <Button variant="secondary" icon={null} style={{ paddingRight: 18 }}>
          Continue to preview <ArrowRight />
        </Button>
      </div>
    </AppShell>
  );
}

/* -------------------------------------------------------------------------- */
/*  Screen 2 — Preview                                                         */
/* -------------------------------------------------------------------------- */

function StatTile({ label, value, sub, valueColor = T.textPrimary }) {
  return (
    <Card style={{ padding: 22 }}>
      <div style={{ fontSize: 15, color: T.textBody, fontWeight: 500 }}>{label}</div>
      <div style={{ marginTop: 10, fontSize: 44, fontWeight: 600, color: valueColor, lineHeight: 1 }}>{value}</div>
      <div style={{ marginTop: 12, fontSize: 13, color: T.textMuted }}>{sub}</div>
    </Card>
  );
}

const PREVIEW_PAPERS = [
  { title: "Sleep-dependent memory consolidation and its role in cognitive performance", authors: "Smith J, van der Berg A, Müller K", venue: "Nature Neuroscience", year: "2024", doi: "10.1038/nn.4521" },
  { title: "Cognitive effects of sleep deprivation: a systematic review and meta-analysis", authors: "Johnson R, Lee S", venue: "Sleep Medicine Reviews", year: "2023", doi: "10.1016/j.smrv.2023.01.002" },
  { title: "Memory reactivation during NREM sleep enhances next-day learning", authors: "Chen Y, Watanabe T, Patel M, García L", venue: "Journal of Neuroscience", year: "2024", doi: "10.1523/jneurosci.1234-23" },
  { title: "REM sleep and emotional memory consolidation: a longitudinal study", authors: "Thompson A, Williams B", venue: "Current Biology", year: "2024", doi: "10.1016/j.cub.2024.02.018" },
  { title: "Working memory capacity and sleep architecture in healthy adults", authors: "Martinez C, Fischer H, de Vries P", venue: "Neuropsychologia", year: "2023", doi: "10.1016/j.neuropsychologia.2023.04.011" },
];

function PaperRow({ paper, last }) {
  return (
    <div style={{
      padding: "16px 0",
      borderBottom: last ? "none" : `1px solid ${T.divider}`,
    }}>
      <div style={{ fontSize: 18, fontWeight: 600, color: T.textPrimary, lineHeight: 1.35 }}>
        {paper.title}
      </div>
      <div style={{ marginTop: 6, fontSize: 14, color: T.textBody }}>{paper.authors}</div>
      <div style={{ marginTop: 6, fontSize: 14, color: T.textMuted, display: "flex", gap: 8, alignItems: "center" }}>
        <span>{paper.venue}</span>
        <span style={{ opacity: 0.5 }}>·</span>
        <span>{paper.year}</span>
        <span style={{ opacity: 0.5 }}>·</span>
        <span style={{ color: T.accent, fontWeight: 500 }}>{paper.doi}</span>
      </div>
    </div>
  );
}

function PreviewScreen() {
  return (
    <AppShell width={1080} height={1280} showMenuDots={true}>
      <Stepper active={1} />

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <StatTile label="Total results" value="1,247" sub="matching your query" />
        <StatTile label="PDF available" value="892" sub="open-access full text" />
        <StatTile label="Previewing" value="10" sub="top results shown below" />
      </div>

      <Card style={{ padding: 22 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <SectionLabel>Results preview</SectionLabel>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ fontSize: 14, color: T.textBody, lineHeight: 1.2 }}>Sort<br/>by</div>
            <div style={{
              background: T.cardInner, border: `1px solid ${T.border}`,
              borderRadius: 10, padding: "10px 14px",
              display: "flex", alignItems: "center", gap: 28,
              fontSize: 16, fontWeight: 600, color: T.textPrimary,
              minWidth: 180,
            }}>
              Relevance <ChevronDown color={T.textMuted} />
            </div>
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          {PREVIEW_PAPERS.map((p, i) => (
            <PaperRow key={p.doi} paper={p} last={false} />
          ))}
          <div style={{ paddingTop: 18, textAlign: "center", color: T.textMuted, fontSize: 13 }}>
            5 more results included in download · scroll to see all 10
          </div>
        </div>
      </Card>

      <Card style={{ padding: 22 }}>
        <SectionLabel>Download settings</SectionLabel>
        <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "180px 1fr auto", gap: 14, alignItems: "end" }}>
          <div>
            <div style={{ fontSize: 14, color: T.textBody, fontWeight: 500, marginBottom: 8 }}>Count</div>
            <TextInput value="50" style={{ textAlign: "center" }} />
          </div>
          <div>
            <div style={{ fontSize: 14, color: T.textBody, fontWeight: 500, marginBottom: 8 }}>Output folder</div>
            <TextInput value="/Users/researcher/papers" />
          </div>
          <Button variant="secondary" style={{ marginBottom: 0 }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
              <window.FolderOpen color={T.textPrimary} /> Browse
            </span>
          </Button>
        </div>
        <div style={{ marginTop: 12, fontSize: 13, color: T.textMuted }}>
          Skipped papers and reasons will be shown on the summary screen
        </div>
      </Card>

      <div style={{ flex: 1 }}></div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 6 }}>
        <Button variant="secondary">
          <window.ArrowLeft /> Back
        </Button>
        <div style={{
          width: 44, height: 44, borderRadius: 22,
          border: `1px solid rgba(255,255,255,0.16)`,
          display: "inline-flex", alignItems: "center", justifyContent: "center",
        }}>
          <ArrowDown color={T.textPrimary} />
        </div>
        <Button variant="secondary">
          Start download <ArrowRight />
        </Button>
      </div>
    </AppShell>
  );
}

Object.assign(window, { SearchScreen, PreviewScreen, StatTile, PaperRow });
