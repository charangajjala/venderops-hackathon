import { useState } from "react"
import { usePolling } from "../hooks/usePolling"
import { getInventory, adjustInventory } from "../api"
import { StatusPanel } from "../components/StatusPanel"

export function Inventory() {
  const { data, error, loading, refresh } = usePolling(getInventory)
  const [busySku, setBusySku] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [customDelta, setCustomDelta] = useState({})

  async function apply(sku, delta) {
    if (!delta) return
    setBusySku(sku)
    setActionError(null)
    try {
      await adjustInventory(sku, delta)
      await refresh()
    } catch (err) {
      setActionError(err.message ?? String(err))
    } finally {
      setBusySku(null)
    }
  }

  return (
    <div>
      <p className="hint">
        Simulate a checkout sale (negative) or a manual restock (positive). This writes straight
        to the real Inventory table - a threshold crossing triggers the same DynamoDB
        Streams → Reorder Checker → AgentCore pipeline the live system runs on, so you can watch
        the agent actually react.
      </p>
      {actionError && <p className="error">{actionError}</p>}
      <StatusPanel loading={loading} error={error} empty={data && data.length === 0} emptyLabel="No inventory items yet.">
        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>On hand</th>
              <th>Reorder threshold</th>
              <th>Reorder quantity</th>
              <th>Adjust</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((item) => {
              const low = Number(item.quantity_on_hand) < Number(item.reorder_threshold)
              const busy = busySku === item.sku
              return (
                <tr key={item.sku} className={low ? "row-alert" : ""}>
                  <td>{item.sku}</td>
                  <td>{item.quantity_on_hand}</td>
                  <td>{item.reorder_threshold}</td>
                  <td>{item.reorder_quantity}</td>
                  <td>
                    <div className="actions">
                      <button disabled={busy} onClick={() => apply(item.sku, -1)}>
                        Sell 1
                      </button>
                      <button disabled={busy} onClick={() => apply(item.sku, -5)}>
                        Sell 5
                      </button>
                      <input
                        type="number"
                        className="delta-input"
                        placeholder="±qty"
                        value={customDelta[item.sku] ?? ""}
                        onChange={(e) =>
                          setCustomDelta({ ...customDelta, [item.sku]: e.target.value })
                        }
                      />
                      <button
                        className="secondary"
                        disabled={busy}
                        onClick={() => apply(item.sku, parseInt(customDelta[item.sku], 10))}
                      >
                        Apply
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </StatusPanel>
    </div>
  )
}
