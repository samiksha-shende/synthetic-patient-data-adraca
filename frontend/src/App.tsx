import { useState, useRef } from 'react'
import axios from 'axios'
import {
  UploadCloud, Play, CheckCircle, Save, AlertTriangle, ShieldCheck, Database, Download, History
} from 'lucide-react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip as RCCartesianTooltip, Legend, ResponsiveContainer,
  LineChart, Line
} from 'recharts'
import './index.css'

function App() {
  const [activeTab, setActiveTab] = useState('ingest')
  const [file, setFile] = useState<File | null>(null)
  const [dbPath, setDbPath] = useState('./data/real_patients.db')
  const [tableName, setTableName] = useState('real_patients')
  const [loading, setLoading] = useState(false)
  
  // Generation state
  const [epsilon, setEpsilon] = useState(1.0)
  const [targetRows, setTargetRows] = useState(500)
  
  // Results
  const [metrics, setMetrics] = useState<any>(null)
  const [pcaData, setPcaData] = useState<any[]>([])
  const [obsHistory, setObsHistory] = useState<any[]>([])

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    if (!file) return alert('Select a file first')
    const formData = new FormData()
    formData.append('file', file)
    setLoading(true)
    try {
      await axios.post('http://localhost:8501/api/ingest/upload', formData)
      alert('Data uploaded successfully! Proceed to the Engine tab.')
      setActiveTab('engine')
    } catch (e: any) {
      alert('Upload failed: ' + e?.response?.data?.detail)
    } finally {
      setLoading(false)
    }
  }

  const handleSqliteLoad = async () => {
    const formData = new FormData()
    formData.append('db_path', dbPath)
    formData.append('table_name', tableName)
    setLoading(true)
    try {
      await axios.post('http://localhost:8501/api/ingest/sqlite', formData)
      alert('Data loaded from SQLite successfully! Proceed to the Engine tab.')
      setActiveTab('engine')
    } catch (e: any) {
      alert('Database load failed: ' + e?.response?.data?.detail)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    const formData = new FormData()
    formData.append('epsilon', epsilon.toString())
    formData.append('target_rows', targetRows.toString())
    setLoading(true)
    try {
      const res = await axios.post('http://localhost:8501/api/generate', formData)
      setMetrics(res.data.metrics)
      setPcaData(res.data.pca)
      alert('Generation complete! Head to validation.')
      setActiveTab('validation')
    } catch (e: any) {
      alert('Generation failed: ' + e?.response?.data?.detail || e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleExportSqlite = async () => {
    const table = prompt('Enter offline table name to append to:', 'synthetic_patients')
    if (!table) return
    const formData = new FormData()
    formData.append('table_name', table)
    try {
      await axios.post('http://localhost:8501/api/export/sqlite', formData)
      alert('Successfully piped to internal sqlite DB!')
    } catch (e: any) {
      alert('Export failed: ' + e?.response?.data?.detail)
    }
  }

  const fetchObservability = async () => {
    try {
      const res = await axios.get('http://localhost:8501/api/observability')
      setObsHistory(res.data.history)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      <div style={{ width: '260px', background: 'rgba(10, 15, 25, 0.9)', borderRight: '1px solid var(--panel-border)', padding: '24px', display: 'flex', flexDirection: 'column' }}>
        <h2 className="text-gradient" style={{ marginBottom: '40px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheck size={28} /> Adraca
        </h2>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button className={activeTab === 'ingest' ? 'btn-primary' : 'btn-secondary'} onClick={() => setActiveTab('ingest')} style={{ textAlign: 'left', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Database size={18} /> Ingestion Stage
          </button>
          <button className={activeTab === 'engine' ? 'btn-primary' : 'btn-secondary'} onClick={() => setActiveTab('engine')} style={{ textAlign: 'left', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Play size={18} /> Engine Setup
          </button>
          <button className={activeTab === 'validation' ? 'btn-primary' : 'btn-secondary'} onClick={() => setActiveTab('validation')} style={{ textAlign: 'left', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <CheckCircle size={18} /> Quality Validation
          </button>
          <button className={activeTab === 'export' ? 'btn-primary' : 'btn-secondary'} onClick={() => setActiveTab('export')} style={{ textAlign: 'left', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Save size={18} /> Compliance Export
          </button>
          <button className={activeTab === 'observability' ? 'btn-primary' : 'btn-secondary'} onClick={() => { setActiveTab('observability'); fetchObservability(); }} style={{ textAlign: 'left', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <History size={18} /> Audit & Drift
          </button>
        </nav>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, padding: '40px', overflowY: 'auto', position: 'relative' }}>
        {loading && (
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
            <div className="glass-panel text-gradient" style={{ fontSize: '24px' }}>Processing Mathematical Operations...</div>
          </div>
        )}

        {/* INGEST TAB */}
        {activeTab === 'ingest' && (
          <div className="glass-panel">
            <h1 className="text-gradient" style={{ marginBottom: '10px' }}>Air-Gapped Ingestion</h1>
            <p className="text-muted" style={{ marginBottom: '30px' }}>Load real patient records locally without reaching out to insecure external servers.</p>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
              <div style={{ border: '1px solid var(--panel-border)', padding: '20px', borderRadius: '8px' }}>
                <h3 style={{ marginBottom: '15px' }}><UploadCloud size={18} /> Upload Dataset</h3>
                <div className="file-upload-zone" onClick={() => fileInputRef.current?.click()}>
                  <p>{file ? file.name : "Click to select CSV or Parquet file"}</p>
                </div>
                <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={(e) => setFile(e.target.files?.[0] || null)} />
                <button className="btn-primary" style={{ marginTop: '20px', width: '100%' }} onClick={handleUpload}>Load File</button>
              </div>

              <div style={{ border: '1px solid var(--panel-border)', padding: '20px', borderRadius: '8px' }}>
                <h3 style={{ marginBottom: '15px' }}><Database size={18} /> SQLite Core Hook</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  <input type="text" placeholder="SQLite Path (e.g. ./data/real.db)" value={dbPath} onChange={e => setDbPath(e.target.value)} />
                  <input type="text" placeholder="Table Name" value={tableName} onChange={e => setTableName(e.target.value)} />
                  <button className="btn-primary" onClick={handleSqliteLoad}>Load Database</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ENGINE TAB */}
        {activeTab === 'engine' && (
          <div className="glass-panel">
            <h1 className="text-gradient" style={{ marginBottom: '10px' }}>Gaussian Copula Synthesizer</h1>
            <p className="text-muted" style={{ marginBottom: '30px' }}>Configure differential privacy boundaries and trigger generation.</p>
            
            <div style={{ maxWidth: '600px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <label className="stat-label">Differential Privacy Budget (ε): {epsilon}</label>
                <input type="range" min="0.1" max="10.0" step="0.1" value={epsilon} onChange={e => setEpsilon(parseFloat(e.target.value))} style={{ width: '100%', marginTop: '10px' }} />
                <span className="text-muted" style={{ fontSize: '12px' }}>Lower values restrict data leakage, higher values prioritize exact statistical parity.</span>
              </div>
              <div>
                <label className="stat-label">Target Synthetic Rows</label>
                <input type="number" min="10" step="10" value={targetRows} onChange={e => setTargetRows(parseInt(e.target.value))} />
              </div>
              <button className="btn-primary" style={{ padding: '15px', fontSize: '16px', marginTop: '10px' }} onClick={handleGenerate}>
                <Play size={18} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
                Launch Pipeline Core
              </button>
            </div>
          </div>
        )}

        {/* VALIDATION TAB */}
        {activeTab === 'validation' && (
          <div>
            <h1 className="text-gradient" style={{ marginBottom: '20px' }}>Fidelity & Privacy Analytics</h1>
            {metrics ? (
              <>
                <div className="scorecard-grid">
                  <div className="glass-panel">
                    <div className="stat-label">Re-identification Risk</div>
                    <div className={`stat-value ${metrics.risk_score > 0.09 ? 'status-bad' : 'status-good'}`}>
                      {(metrics.risk_score * 100).toFixed(2)}%
                    </div>
                    <div className="text-muted" style={{ fontSize: '12px' }}>Threshold: &lt;9.00%</div>
                  </div>
                  <div className="glass-panel">
                    <div className="stat-label">Exact Match Rate (DCR)</div>
                    <div className={`stat-value ${metrics.exact_match_rate > 0 ? 'status-bad' : 'status-good'}`}>
                      {(metrics.exact_match_rate * 100).toFixed(3)}%
                    </div>
                  </div>
                  <div className="glass-panel">
                    <div className="stat-label">KS Complement (Utility)</div>
                    <div className={`stat-value ${metrics.avg_ks > 0.85 ? 'status-good' : 'status-warn'}`}>
                      {(metrics.avg_ks * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="glass-panel">
                    <div className="stat-label">Info Theory (Hellinger)</div>
                    <div className="stat-value text-gradient">
                      {metrics.avg_hellinger.toFixed(4)}
                    </div>
                  </div>
                </div>

                <div className="glass-panel" style={{ height: '400px', marginBottom: '20px' }}>
                  <h3 style={{ marginBottom: '15px' }}>Principal Component Analysis (PCA) Overlay</h3>
                  <ResponsiveContainer width="100%" height="85%">
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <XAxis type="number" dataKey="PC1" name="PC 1" stroke="var(--text-secondary)" />
                      <YAxis type="number" dataKey="PC2" name="PC 2" stroke="var(--text-secondary)" />
                      <RCCartesianTooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)', backdropFilter: 'blur(10px)' }}/>
                      <Legend />
                      <Scatter name="Real Data" data={pcaData.filter(d => d.Dataset === 'Real')} fill="var(--accent-blue)" shape="circle" fillOpacity={0.6} />
                      <Scatter name="Synthetic Data" data={pcaData.filter(d => d.Dataset === 'Synthetic')} fill="var(--accent-purple)" shape="diamond" fillOpacity={0.8} />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
                
                {metrics.is_compliant ? (
                   <div style={{ background: 'rgba(0, 230, 118, 0.1)', border: '1px solid var(--accent-green)', padding: '20px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '15px' }}>
                     <ShieldCheck size={32} color="var(--accent-green)" />
                     <div>
                       <h3 style={{ color: 'var(--accent-green)', marginBottom: '5px' }}>EMA Policy 0070 Compliant</h3>
                       <p className="text-muted">Dataset is mathematically cleared for safe export.</p>
                     </div>
                   </div>
                ) : (
                   <div style={{ background: 'rgba(255, 61, 0, 0.1)', border: '1px solid var(--accent-red)', padding: '20px', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '15px' }}>
                     <AlertTriangle size={32} color="var(--accent-red)" />
                     <div>
                       <h3 style={{ color: 'var(--accent-red)', marginBottom: '5px' }}>Compliance Violation</h3>
                       <p className="text-muted">Re-identification thresholds exceeded. Tuning the epsilon budget is required.</p>
                     </div>
                   </div>
                )}
              </>
            ) : (
              <p className="text-muted">Run the engine first to populate validation metrics.</p>
            )}
          </div>
        )}

        {/* EXPORT TAB */}
        {activeTab === 'export' && (
          <div className="glass-panel">
            <h1 className="text-gradient" style={{ marginBottom: '30px' }}>Immutable Export</h1>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
              <div style={{ border: '1px solid var(--panel-border)', padding: '20px', borderRadius: '8px' }}>
                <h3 style={{ marginBottom: '15px' }}><Download size={18} /> Direct Files</h3>
                <p className="text-muted" style={{ marginBottom: '20px' }}>Not recommended for massive datasets due to browser memory limits.</p>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button className="btn-secondary" disabled={!metrics}>CSV Download</button>
                  <button className="btn-secondary" disabled={!metrics}>Parquet Network</button>
                </div>
              </div>

              <div style={{ border: '1px solid var(--panel-border)', padding: '20px', borderRadius: '8px' }}>
                <h3 style={{ marginBottom: '15px' }}><Database size={18} /> SQLite Persistent Pipe</h3>
                <p className="text-muted" style={{ marginBottom: '20px' }}>Stream rows directly into the air-gapped container's disk mount.</p>
                <button className="btn-primary" onClick={handleExportSqlite} disabled={!metrics}>Execute Pipeline</button>
              </div>
            </div>

            <div style={{ marginTop: '30px', border: '1px solid var(--panel-border)', padding: '20px', borderRadius: '8px' }}>
              <h3 style={{ marginBottom: '15px' }}>Compliance Attestation</h3>
              <p className="text-muted" style={{ marginBottom: '20px' }}>Generate the PDF Cryptographic Record holding the mathematical proofs for auditing agencies.</p>
              <a href="http://localhost:8501/api/export/pdf" download="Adraca_Certificate.pdf">
                <button className="btn-primary" disabled={!metrics}>Generate Certificate PDF</button>
              </a>
            </div>
          </div>
        )}

        {/* OBSERVABILITY TAB */}
        {activeTab === 'observability' && (
          <div className="glass-panel">
            <h1 className="text-gradient" style={{ marginBottom: '20px' }}>Audit Telemetry & Drift Tracking</h1>
            {obsHistory.length > 0 ? (
              <>
                 <div style={{ height: '300px', marginBottom: '30px' }}>
                   <ResponsiveContainer width="100%" height="100%">
                     <LineChart data={obsHistory}>
                       <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                       <XAxis dataKey="timestamp" hide />
                       <YAxis stroke="var(--text-secondary)" />
                       <RCCartesianTooltip contentStyle={{ backgroundColor: 'var(--panel-bg)', borderColor: 'var(--panel-border)' }} />
                       <Legend />
                       <Line type="monotone" name="Utility (KS)" dataKey="ks_utility" stroke="var(--accent-blue)" strokeWidth={3} />
                       <Line type="monotone" name="Risk Profile" dataKey="risk" stroke="var(--accent-red)" strokeWidth={2} />
                     </LineChart>
                   </ResponsiveContainer>
                 </div>
                 
                 <div style={{ overflowX: 'auto' }}>
                   <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse', color: 'var(--text-primary)' }}>
                     <thead>
                       <tr style={{ borderBottom: '1px solid var(--panel-border)', color: 'var(--text-secondary)' }}>
                         <th style={{ padding: '10px' }}>Timestamp</th>
                         <th style={{ padding: '10px' }}>ε Budget</th>
                         <th style={{ padding: '10px' }}>Utility %</th>
                         <th style={{ padding: '10px' }}>Risk %</th>
                         <th style={{ padding: '10px' }}>Passed</th>
                       </tr>
                     </thead>
                     <tbody>
                       {obsHistory.map((run, i) => (
                         <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                           <td style={{ padding: '10px', fontSize: '13px' }}>{run.timestamp}</td>
                           <td style={{ padding: '10px' }}>{run.epsilon}</td>
                           <td style={{ padding: '10px' }}>{(run.ks_utility * 100).toFixed(1)}%</td>
                           <td style={{ padding: '10px' }}>{(run.risk * 100).toFixed(2)}%</td>
                           <td style={{ padding: '10px' }}>{run.compliant ? '✅' : '🚨'}</td>
                         </tr>
                       ))}
                     </tbody>
                   </table>
                 </div>
              </>
            ) : (
              <p className="text-muted">No telemetry found in audit.jsonl yet.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default App
