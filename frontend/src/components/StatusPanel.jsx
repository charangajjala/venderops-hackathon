export function StatusPanel({ loading, error, empty, emptyLabel, children }) {
  if (loading) return <p className="hint">Loading…</p>
  if (error) return <p className="error">Error: {error}</p>
  if (empty) return <p className="hint">{emptyLabel}</p>
  return children
}
