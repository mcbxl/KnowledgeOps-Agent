import { useEffect, useMemo, useState } from 'react'
import ReactFlow, { Background, Controls } from 'reactflow'
import {
  AlertTriangle,
  BookOpen,
  Boxes,
  ClipboardCheck,
  FilePlus2,
  Gauge,
  GitBranch,
  Loader2,
  MessageSquareText,
  Search,
  Sparkles,
  Upload,
} from 'lucide-react'
import {
  ask,
  evaluateRetrieval,
  getOpsReport,
  ingestText,
  ingestUrl,
  listDocuments,
  runAgent,
  search,
  uploadDocument,
} from './lib/api'

const tabs = [
  { id: 'ingest', label: 'Ingest', icon: FilePlus2 },
  { id: 'search', label: 'Search', icon: Search },
  { id: 'ask', label: 'Ask', icon: MessageSquareText },
  { id: 'ops', label: 'Ops', icon: Sparkles },
  { id: 'agent', label: 'Agent', icon: ClipboardCheck },
  { id: 'eval', label: 'Eval', icon: Gauge },
  { id: 'graph', label: 'Graph', icon: GitBranch },
]

export default function App() {
  const [activeTab, setActiveTab] = useState('ingest')
  const [documents, setDocuments] = useState([])
  const [report, setReport] = useState(null)
  const [status, setStatus] = useState('')
  const [busy, setBusy] = useState(false)

  async function refresh() {
    const [docs, ops] = await Promise.all([listDocuments(), getOpsReport()])
    setDocuments(docs)
    setReport(ops)
  }

  useEffect(() => {
    refresh().catch((error) => setStatus(error.message))
  }, [])

  async function run(action, successMessage) {
    setBusy(true)
    setStatus('')
    try {
      await action()
      await refresh()
      setStatus(successMessage)
    } catch (error) {
      setStatus(error.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <Boxes size={25} />
          <div>
            <strong>KnowledgeOps</strong>
            <span>Agent workspace</span>
          </div>
        </div>

        <nav className="nav">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                className={activeTab === tab.id ? 'active' : ''}
                onClick={() => setActiveTab(tab.id)}
                title={tab.label}
              >
                <Icon size={18} />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </nav>

        <div className="sidebarStats">
          <span>Documents</span>
          <strong>{documents.length}</strong>
          <span>Chunks</span>
          <strong>{report?.chunk_count ?? 0}</strong>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>{tabs.find((tab) => tab.id === activeTab)?.label}</h1>
            <p>Operate, search, diagnose, and reorganize your knowledge base.</p>
          </div>
          {busy && <Loader2 className="spin" size={22} />}
        </header>

        {status && <div className="status">{status}</div>}

        {activeTab === 'ingest' && <IngestPanel run={run} documents={documents} />}
        {activeTab === 'search' && <SearchPanel />}
        {activeTab === 'ask' && <AskPanel />}
        {activeTab === 'ops' && <OpsPanel report={report} refresh={refresh} />}
        {activeTab === 'agent' && <AgentPanel />}
        {activeTab === 'eval' && <EvalPanel />}
        {activeTab === 'graph' && <GraphPanel report={report} />}
      </main>
    </div>
  )
}

function IngestPanel({ run, documents }) {
  const [title, setTitle] = useState('React 18 Migration Notes')
  const [content, setContent] = useState(
    '# React 18\n\nReact 18 recommends using createRoot for rendering applications.\n\n## Legacy API\n\nOlder documents may still mention ReactDOM.render, which is deprecated for new React 18 roots.',
  )
  const [url, setUrl] = useState('')

  return (
    <section className="grid two">
      <form
        className="panel"
        onSubmit={(event) => {
          event.preventDefault()
          run(() => ingestText({ title, content, source_type: 'markdown', tags: [] }), 'Document ingested.')
        }}
      >
        <div className="panelHeader">
          <BookOpen size={18} />
          <h2>Text or Markdown</h2>
        </div>
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          Content
          <textarea value={content} onChange={(event) => setContent(event.target.value)} />
        </label>
        <button className="primary" type="submit">
          <FilePlus2 size={17} />
          Ingest
        </button>
      </form>

      <div className="stack">
        <form
          className="panel compact"
          onSubmit={(event) => {
            event.preventDefault()
            run(() => ingestUrl({ url, tags: [] }), 'URL ingested.')
          }}
        >
          <div className="panelHeader">
            <Search size={18} />
            <h2>Web Page</h2>
          </div>
          <label>
            URL
            <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://..." />
          </label>
          <button className="primary" type="submit">
            <FilePlus2 size={17} />
            Fetch
          </button>
        </form>

        <div className="panel compact">
          <div className="panelHeader">
            <Upload size={18} />
            <h2>Upload File</h2>
          </div>
          <input
            type="file"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) run(() => uploadDocument(file), 'File uploaded.')
            }}
          />
        </div>

        <DocumentList documents={documents} />
      </div>
    </section>
  )
}

function SearchPanel() {
  const [query, setQuery] = useState('React 18 createRoot')
  const [intent, setIntent] = useState('auto')
  const [hits, setHits] = useState([])
  const [loading, setLoading] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    try {
      setHits(await search({ query, intent, limit: 10 }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel">
      <form className="queryBar" onSubmit={submit}>
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
        <select value={intent} onChange={(event) => setIntent(event.target.value)}>
          <option value="auto">Auto</option>
          <option value="fact">Fact</option>
          <option value="concept">Concept</option>
          <option value="summary">Summary</option>
          <option value="compare">Compare</option>
        </select>
        <button className="primary" type="submit">
          {loading ? <Loader2 className="spin" size={17} /> : <Search size={17} />}
          Search
        </button>
      </form>
      <HitList hits={hits} />
    </section>
  )
}

function AskPanel() {
  const [query, setQuery] = useState('Which rendering API should React 18 use?')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    try {
      setResult(await ask({ query, intent: 'auto', limit: 8, answer_mode: 'knowledge_only' }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="grid two">
      <form className="panel compact" onSubmit={submit}>
        <div className="panelHeader">
          <MessageSquareText size={18} />
          <h2>Citation QA</h2>
        </div>
        <textarea value={query} onChange={(event) => setQuery(event.target.value)} />
        <button className="primary" type="submit">
          {loading ? <Loader2 className="spin" size={17} /> : <MessageSquareText size={17} />}
          Ask
        </button>
      </form>
      <div className="panel answer">
        {result ? (
          <>
            <div className="answerMeta">
              <span>Intent: {result.detected_intent}</span>
              <span>Confidence: {Math.round(result.confidence * 100)}%</span>
            </div>
            <pre>{result.answer}</pre>
            <h3>Citations</h3>
            <CitationList citations={result.citations} />
          </>
        ) : (
          <p className="empty">Ask a question to get a cited answer.</p>
        )}
      </div>
    </section>
  )
}

function OpsPanel({ report, refresh }) {
  if (!report) return <div className="panel">Loading report...</div>
  return (
    <section className="stack">
      <div className="metrics">
        <Metric label="Documents" value={report.document_count} />
        <Metric label="Chunks" value={report.chunk_count} />
        <Metric label="Quality" value={`${Math.round(report.average_quality_score * 100)}%`} />
        <button className="primary" onClick={refresh}>
          <Sparkles size={17} />
          Refresh
        </button>
      </div>
      <div className="grid two">
        <div className="panel">
          <div className="panelHeader">
            <AlertTriangle size={18} />
            <h2>Issues</h2>
          </div>
          {report.issues.length === 0 ? (
            <p className="empty">No issues detected yet.</p>
          ) : (
            report.issues.map((issue, index) => (
              <article className={`issue ${issue.severity}`} key={`${issue.kind}-${index}`}>
                <strong>{issue.title}</strong>
                <span>
                  {issue.kind} / {issue.severity} / confidence {Math.round(issue.confidence * 100)}%
                </span>
                <p>{issue.description}</p>
                {issue.evidence?.length > 0 && <small>Evidence: {issue.evidence.slice(0, 4).join(' | ')}</small>}
                {issue.suggested_actions?.length > 0 && (
                  <ul>
                    {issue.suggested_actions.map((action) => <li key={action}>{action}</li>)}
                  </ul>
                )}
              </article>
            ))
          )}
        </div>
        <div className="panel">
          <div className="panelHeader">
            <Sparkles size={18} />
            <h2>Generated Assets</h2>
          </div>
          <h3>FAQ</h3>
          {report.faqs.map((faq, index) => (
            <article className="faq" key={index}>
              <strong>{faq.question}</strong>
              <p>{faq.answer}</p>
            </article>
          ))}
          <h3>Learning Path</h3>
          <ol className="path">
            {report.learning_path.map((step) => <li key={step}>{step}</li>)}
          </ol>
          <h3>Topic Coverage</h3>
          <div className="coverageGrid">
            {report.topic_coverage.map((topic) => (
              <article className={`coverage ${topic.quality_hint}`} key={topic.topic}>
                <strong>{topic.topic}</strong>
                <span>{topic.document_count} docs · {topic.chunk_count} chunks</span>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function AgentPanel() {
  const [objective, setObjective] = useState('Diagnose knowledge-base quality and generate governance actions.')
  const [focus, setFocus] = useState('overview')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    try {
      setResult(await runAgent({ objective, focus }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="grid two agentGrid">
      <form className="panel compact" onSubmit={submit}>
        <div className="panelHeader">
          <ClipboardCheck size={18} />
          <h2>KnowledgeOps Agent</h2>
        </div>
        <label>
          Objective
          <textarea value={objective} onChange={(event) => setObjective(event.target.value)} />
        </label>
        <label>
          Focus
          <select value={focus} onChange={(event) => setFocus(event.target.value)}>
            <option value="overview">Overview</option>
            <option value="quality">Quality</option>
            <option value="conflict">Conflict</option>
            <option value="retrieval">Retrieval</option>
            <option value="growth">Growth</option>
          </select>
        </label>
        <button className="primary" type="submit">
          {loading ? <Loader2 className="spin" size={17} /> : <ClipboardCheck size={17} />}
          Run Agent
        </button>
      </form>

      <div className="panel agentResult">
        {result ? (
          <>
            <div className="answerMeta">
              <span>Focus: {result.focus}</span>
              <span>{new Date(result.generated_at).toLocaleString()}</span>
            </div>
            <p className="summary">{result.executive_summary}</p>
            <h3>Workflow</h3>
            {result.stages.map((stage) => (
              <article className={`stage ${stage.status}`} key={stage.name}>
                <strong>{stage.name}</strong>
                <span>{stage.status}</span>
                <p>{stage.observation}</p>
                {stage.evidence.length > 0 && <small>Evidence: {stage.evidence.join(' / ')}</small>}
                {stage.next_actions.length > 0 && (
                  <ul>
                    {stage.next_actions.map((action) => <li key={action}>{action}</li>)}
                  </ul>
                )}
              </article>
            ))}
            <h3>Backlog</h3>
            {result.recommended_backlog.map((item) => (
              <article className="backlog" key={`${item.priority}-${item.item}`}>
                <strong>{item.priority} · {item.item}</strong>
                <p>{item.reason}</p>
              </article>
            ))}
          </>
        ) : (
          <p className="empty">Run the agent to generate a governance workflow.</p>
        )}
      </div>
    </section>
  )
}

function EvalPanel() {
  const [queries, setQueries] = useState('React createRoot\nHybrid search\nRerank')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    try {
      const queryList = queries
        .split('\n')
        .map((query) => query.trim())
        .filter(Boolean)
      setResult(await evaluateRetrieval({ queries: queryList, limit: 5 }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="grid two">
      <form className="panel compact" onSubmit={submit}>
        <div className="panelHeader">
          <Gauge size={18} />
          <h2>Retrieval Evaluation</h2>
        </div>
        <label>
          Benchmark queries
          <textarea value={queries} onChange={(event) => setQueries(event.target.value)} />
        </label>
        <button className="primary" type="submit">
          {loading ? <Loader2 className="spin" size={17} /> : <Gauge size={17} />}
          Evaluate
        </button>
      </form>

      <div className="panel">
        {result ? (
          <>
            <div className="metrics evalMetrics">
              <Metric label="Avg Top Score" value={result.average_top_score} />
              <Metric label="Citation Ready" value={`${Math.round(result.citation_ready_rate * 100)}%`} />
            </div>
            {result.cases.map((item) => (
              <article className="evalCase" key={item.query}>
                <strong>{item.query}</strong>
                <span>{item.hit_count} hits · top score {item.top_score}</span>
                <p>{item.recommendation}</p>
              </article>
            ))}
          </>
        ) : (
          <p className="empty">Run benchmark queries to inspect retrieval quality.</p>
        )}
      </div>
    </section>
  )
}

function GraphPanel({ report }) {
  const flow = useMemo(() => {
    const graph = report?.graph || { nodes: [], edges: [] }
    const nodes = graph.nodes.map((node, index) => ({
      id: node.id,
      data: { label: node.label },
      position: {
        x: node.type === 'document' ? 40 : node.type === 'section' ? 360 : 690,
        y: 48 * index,
      },
      className: node.type,
    }))
    const edges = graph.edges.map((edge, index) => ({
      id: `edge-${index}`,
      source: edge.source,
      target: edge.target,
      animated: edge.type === 'mentions',
    }))
    return { nodes, edges }
  }, [report])

  return (
    <section className="panel graphPanel">
      {flow.nodes.length ? (
        <ReactFlow nodes={flow.nodes} edges={flow.edges} fitView>
          <Background />
          <Controls />
        </ReactFlow>
      ) : (
        <p className="empty">Ingest documents to build the knowledge graph.</p>
      )}
    </section>
  )
}

function DocumentList({ documents }) {
  return (
    <div className="panel documentList">
      <div className="panelHeader">
        <BookOpen size={18} />
        <h2>Documents</h2>
      </div>
      {documents.length === 0 ? (
        <p className="empty">No documents yet.</p>
      ) : (
        documents.map((doc) => (
          <article className="documentRow" key={doc.id}>
            <strong>{doc.title}</strong>
            <span>{doc.source_type} · {doc.chunk_count} chunks</span>
            <p>{doc.summary}</p>
          </article>
        ))
      )}
    </div>
  )
}

function HitList({ hits }) {
  return (
    <div className="hits">
      {hits.map((hit) => (
        <article className="hit" key={hit.chunk_id}>
          <div>
            <strong>{hit.title}</strong>
            <span>{hit.section_path.join(' > ')}</span>
          </div>
          <p>{hit.snippet}</p>
          <footer>
            <span>Score {hit.score}</span>
            <span>BM25 {hit.lexical_score}</span>
            <span>Vector {hit.vector_score}</span>
            <span>Rerank {hit.rerank_score}</span>
          </footer>
        </article>
      ))}
    </div>
  )
}

function CitationList({ citations }) {
  return citations.map((citation) => (
    <article className="citation" key={citation.chunk_id}>
      <strong>{citation.title}</strong>
      <span>{citation.section_path.join(' > ')}</span>
      <p>{citation.snippet}</p>
    </article>
  ))
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
