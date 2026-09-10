import { useState } from "react"
import { usePolling } from "../hooks/usePolling"
import { getRfqs, approveRfq, rejectRfq } from "../api"
import { StatusPanel } from "../components/StatusPanel"

export function Rfqs() {
  const { data, error, loading, refresh } = usePolling(getRfqs)
  const [busyId, setBusyId] = useState(null)
  const [actionError, setActionError] = useState(null)

  async function handleDecision(rfqId, action) {
    setBusyId(rfqId)
    setActionError(null)
    try {
      await (action === "approve" ? approveRfq(rfqId) : rejectRfq(rfqId))
      await refresh()
    } catch (err) {
      setActionError(err.message ?? String(err))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      {actionError && <p className="error">{actionError}</p>}
      <StatusPanel loading={loading} error={error} empty={data && data.length === 0} emptyLabel="No RFQs yet.">
        <table>
          <thead>
            <tr>
              <th>RFQ</th>
              <th>SKU</th>
              <th>Qty</th>
              <th>Vendor</th>
              <th>Status</th>
              <th>Quote</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((rfq) => {
              const decidable = rfq.quote && !["awarded", "rejected"].includes(rfq.status)
              return (
                <tr key={rfq.rfq_id} className={decidable ? "row-pending" : ""}>
                  <td title={rfq.rfq_id}>{rfq.rfq_id.slice(0, 8)}</td>
                  <td>{rfq.sku}</td>
                  <td>{rfq.quantity}</td>
                  <td>{rfq.vendor_id}</td>
                  <td>{rfq.status}</td>
                  <td>
                    {rfq.quote
                      ? `$${rfq.quote.unit_price}/unit, ${rfq.quote.lead_time_days}d lead time`
                      : "—"}
                  </td>
                  <td>
                    {decidable && (
                      <div className="actions">
                        <button
                          disabled={busyId === rfq.rfq_id}
                          onClick={() => handleDecision(rfq.rfq_id, "approve")}
                        >
                          Approve
                        </button>
                        <button
                          className="secondary"
                          disabled={busyId === rfq.rfq_id}
                          onClick={() => handleDecision(rfq.rfq_id, "reject")}
                        >
                          Reject
                        </button>
                      </div>
                    )}
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
