import { useEffect, useMemo, useState } from 'react'
import ReactFlow, { Background, Controls } from 'reactflow'
import {
  AlertTriangle,
  Activity,
  BookOpen,
  Boxes,
  ClipboardCheck,
  FilePlus2,
  Gauge,
  GitBranch,
  ListChecks,
  Loader2,
  MessageSquareText,
  Search,
  Sparkles,
  Upload,
} from 'lucide-react'
import {
  ask,
  createBenchmark,
  evaluateRetrieval,
  getDocument,
  getOpsReport,
  getRuntimeStatus,
  ingestText,
  ingestUrl,
  createOpsReportTask,
  listBenchmarks,
  listTasks,
  listDocuments,
  runAgent,
  runBenchmark,
  search,
  uploadDocument,
} from './lib/api'

const tabs = [
  { id: 'ingest', label: 'Ingest', icon: FilePlus2 },
  { id: 'search', label: 'Search', icon: Search },
  { id: 'ask', label: 'Ask', icon: MessageSquareText },
  { id: 'ops', label: 'Ops', icon: Sparkles },
  { id: 'agent', label: 'Agent', icon: ClipboardCheck },
  { id: 'runtime', label: 'Runtime', icon: Activity },
  { id: 'eval', label: 'Eval', icon: Gauge },
  { id: 'tasks', label: 'Tasks', icon: ListChecks },
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
        {activeTab === 'runtime' && <RuntimePanel />}
        {activeTab === 'eval' && <EvalPanel />}
        {activeTab === 'tasks' && <TasksPanel />}
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
  const [selectedDocumentId, setSelectedDocumentId] = useState(null)
  const [documentDetail, setDocumentDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  async function inspectDocument(documentId) {
    setSelectedDocumentId(documentId)
    setLoadingDetail(true)
    try {
      setDocumentDetail(await getDocument(documentId))
    } finally {
      setLoadingDetail(false)
    }
  }

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

        <DocumentList
          documents={documents}
          selectedDocumentId={selectedDocumentId}
          onSelect={inspectDocument}
        />
      </div>
      <DocumentInspector detail={documentDetail} loading={loadingDetail} />
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
              {result.grounding && <span>Grounding: {result.grounding.status}</span>}
            </div>
            <pre>{result.answer}</pre>
            {result.grounding && <GroundingAudit grounding={result.grounding} />}
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

function GroundingAudit({ grounding }) {
  return (
    <div className={`groundingAudit ${grounding.status}`}>
      <div>
        <strong>{Math.round(grounding.groundedness_score * 100)}%</strong>
        <span>Groundedness</span>
      </div>
      <div>
        <strong>{Math.round(grounding.evidence_coverage * 100)}%</strong>
        <span>Evidence coverage</span>
      </div>
      <div>
        <strong>{grounding.citation_count}</strong>
        <span>Citations</span>
      </div>
      {grounding.unsupported_terms.length > 0 && (
        <p>Unsupported terms: {grounding.unsupported_terms.slice(0, 8).join(', ')}</p>
      )}
      {grounding.warnings.length > 0 && (
        <ul>
          {grounding.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
    </div>
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

function RuntimePanel() {
  const [runtime, setRuntime] = useState(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  async function refresh() {
    setLoading(true)
    setStatus('')
    try {
      setRuntime(await getRuntimeStatus())
    } catch (error) {
      setStatus(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  return (
    <section className="stack">
      <div className="metrics runtimeMetrics">
        <Metric label="Environment" value={runtime?.environment || '...'} />
        <Metric label="Runtime" value={runtime?.status || 'loading'} />
        <Metric label="Components" value={runtime?.components?.length ?? 0} />
        <button className="primary" onClick={refresh} type="button">
          {loading ? <Loader2 className="spin" size={17} /> : <Activity size={17} />}
          Refresh
        </button>
      </div>

      {status && <div className="status">{status}</div>}

      <div className="grid two">
        <div className="panel">
          <div className="panelHeader">
            <Activity size={18} />
            <h2>Runtime Components</h2>
          </div>
          {!runtime ? (
            <p className="empty">Loading runtime status...</p>
          ) : (
            <div className="runtimeList">
              {runtime.components.map((component) => (
                <article className={`runtimeComponent ${component.status}`} key={component.name}>
                  <div>
                    <strong>{component.name}</strong>
                    <span>{component.status}</span>
                  </div>
                  <small>{component.provider || 'not configured'}</small>
                  <p>{component.detail}</p>
                  {component.checks.length > 0 && (
                    <footer>
                      {component.checks.map((check) => (
                        <span key={check}>{check}</span>
                      ))}
                    </footer>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panelHeader">
            <ClipboardCheck size={18} />
            <h2>Readiness Recommendations</h2>
          </div>
          {!runtime ? (
            <p className="empty">Runtime checks will appear here.</p>
          ) : (
            <div className="recommendationList">
              {runtime.recommendations.map((item) => (
                <article className="recommendation" key={item}>
                  <span>{item}</span>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function EvalPanel() {
  const [queries, setQueries] = useState('React createRoot\nHybrid search\nRerank')
  const [benchmarkName, setBenchmarkName] = useState('Core retrieval baseline')
  const [benchmarks, setBenchmarks] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  async function refreshBenchmarks() {
    setBenchmarks(await listBenchmarks())
  }

  useEffect(() => {
    refreshBenchmarks().catch((error) => setStatus(error.message))
  }, [])

  function queryList() {
    return queries
      .split('\n')
      .map((query) => query.trim())
      .filter(Boolean)
  }

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setStatus('')
    try {
      setResult(await evaluateRetrieval({ queries: queryList(), limit: 5 }))
    } catch (error) {
      setStatus(error.message)
    } finally {
      setLoading(false)
    }
  }

  async function saveBenchmark() {
    setLoading(true)
    setStatus('')
    try {
      await createBenchmark({
        name: benchmarkName,
        limit: 5,
        cases: queryList().map((query) => ({ query })),
      })
      await refreshBenchmarks()
      setStatus('Benchmark saved.')
    } catch (error) {
      setStatus(error.message)
    } finally {
      setLoading(false)
    }
  }

  async function runSavedBenchmark(benchmarkId) {
    setLoading(true)
    setStatus('')
    try {
      setResult(await runBenchmark(benchmarkId))
    } catch (error) {
      setStatus(error.message)
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
          Benchmark name
          <input value={benchmarkName} onChange={(event) => setBenchmarkName(event.target.value)} />
        </label>
        <label>
          Benchmark queries
          <textarea value={queries} onChange={(event) => setQueries(event.target.value)} />
        </label>
        <div className="taskActions">
          <button className="primary" type="submit">
            {loading ? <Loader2 className="spin" size={17} /> : <Gauge size={17} />}
            Evaluate
          </button>
          <button className="secondary" onClick={saveBenchmark} type="button">
            Save Benchmark
          </button>
        </div>
        {status && <p className="taskStatus">{status}</p>}
      </form>

      <div className="stack">
        <div className="panel">
        {result ? (
          <>
            {result.benchmark_name && <p className="summary">Benchmark: {result.benchmark_name}</p>}
            <div className="metrics evalMetrics">
              <Metric label="Avg Top Score" value={result.average_top_score} />
              <Metric label="Citation Ready" value={`${Math.round(result.citation_ready_rate * 100)}%`} />
              {result.expected_hit_rate !== null && result.expected_hit_rate !== undefined && (
                <Metric label="Expected Hit" value={`${Math.round(result.expected_hit_rate * 100)}%`} />
              )}
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

        <div className="panel">
          <div className="panelHeader">
            <ListChecks size={18} />
            <h2>Saved Benchmarks</h2>
          </div>
          {benchmarks.length === 0 ? (
            <p className="empty">No saved benchmarks yet.</p>
          ) : (
            <div className="benchmarkList">
              {benchmarks.map((benchmark) => (
                <article className="benchmarkRow" key={benchmark.id}>
                  <div>
                    <strong>{benchmark.name}</strong>
                    <span>{benchmark.cases.length} cases / top {benchmark.limit}</span>
                  </div>
                  <button className="secondary" type="button" onClick={() => runSavedBenchmark(benchmark.id)}>
                    Run
                  </button>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function TasksPanel() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  async function refresh() {
    setLoading(true)
    try {
      setTasks(await listTasks())
    } finally {
      setLoading(false)
    }
  }

  async function createTask() {
    setLoading(true)
    setStatus('')
    try {
      const task = await createOpsReportTask()
      setStatus(`Created task ${task.id.slice(0, 8)}.`)
      setTasks(await listTasks())
    } catch (error) {
      setStatus(error.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh().catch((error) => setStatus(error.message))
  }, [])

  return (
    <section className="stack">
      <div className="panel taskToolbar">
        <div className="panelHeader">
          <ListChecks size={18} />
          <h2>Operations Tasks</h2>
        </div>
        <div className="taskActions">
          <button className="primary" onClick={createTask} type="button">
            {loading ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
            Generate Ops Report
          </button>
          <button className="secondary" onClick={refresh} type="button">
            Refresh
          </button>
        </div>
        {status && <p className="taskStatus">{status}</p>}
      </div>
      <div className="panel">
        {tasks.length === 0 ? (
          <p className="empty">No tasks yet.</p>
        ) : (
          <div className="taskList">
            {tasks.map((task) => (
              <article className={`taskRow ${task.status}`} key={task.id}>
                <div>
                  <strong>{task.title}</strong>
                  <span>{task.task_type} · {task.status}</span>
                </div>
                <small>{new Date(task.updated_at).toLocaleString()}</small>
                {task.result && (
                  <footer>
                    <span>{task.result.document_count} docs</span>
                    <span>{task.result.chunk_count} chunks</span>
                    <span>{task.result.issue_count} issues</span>
                    <span>{Math.round(task.result.quality_score * 100)}% quality</span>
                  </footer>
                )}
                {task.error && <p>{task.error}</p>}
              </article>
            ))}
          </div>
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

function DocumentList({ documents, selectedDocumentId, onSelect }) {
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
          <button
            className={`documentRow ${selectedDocumentId === doc.id ? 'selected' : ''}`}
            key={doc.id}
            onClick={() => onSelect(doc.id)}
            type="button"
          >
            <strong>{doc.title}</strong>
            <span>{doc.source_type} · {doc.chunk_count} chunks</span>
            <p>{doc.summary}</p>
          </button>
        ))
      )}
    </div>
  )
}

function DocumentInspector({ detail, loading }) {
  if (loading) {
    return (
      <div className="panel inspector">
        <Loader2 className="spin" size={20} />
        <p>Loading document structure...</p>
      </div>
    )
  }
  if (!detail) {
    return (
      <div className="panel inspector">
        <div className="panelHeader">
          <BookOpen size={18} />
          <h2>Document Inspector</h2>
        </div>
        <p className="empty">Select a document to inspect chunking, metadata, and index fields.</p>
      </div>
    )
  }
  return (
    <div className="panel inspector">
      <div className="panelHeader">
        <BookOpen size={18} />
        <h2>Document Inspector</h2>
      </div>
      <div className="inspectorMeta">
        <span>{detail.source_type}</span>
        <span>{detail.chunk_count} chunks</span>
        <span>{detail.tags.join(', ') || 'no tags'}</span>
      </div>
      <h3>{detail.title}</h3>
      <p className="preview">{detail.content_preview}</p>
      <small>Hash: {detail.content_hash.slice(0, 18)}...</small>
      <h3>Chunks</h3>
      <div className="chunkList">
        {detail.chunks.map((chunk) => (
          <article className="chunkRow" key={chunk.id}>
            <div>
              <strong>#{chunk.order_index + 1}</strong>
              <span>{chunk.section_path.join(' > ')}</span>
            </div>
            <p>{chunk.text}</p>
            <footer>
              <span>{chunk.token_count} tokens</span>
              <span>{chunk.embedding_dimensions} dims</span>
              <span>{chunk.tags.join(', ') || 'no tags'}</span>
            </footer>
          </article>
        ))}
      </div>
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
