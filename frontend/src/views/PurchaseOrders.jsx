import { usePolling } from "../hooks/usePolling"
import { getPurchaseOrders } from "../api"
import { StatusPanel } from "../components/StatusPanel"

export function PurchaseOrders() {
  const { data, error, loading } = usePolling(getPurchaseOrders)

  return (
    <StatusPanel loading={loading} error={error} empty={data && data.length === 0} emptyLabel="No purchase orders issued yet.">
      <table>
        <thead>
          <tr>
            <th>PO</th>
            <th>SKU</th>
            <th>Vendor</th>
            <th>Qty</th>
            <th>Unit price</th>
            <th>Total</th>
            <th>Issued</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((po) => (
            <tr key={po.po_id}>
              <td title={po.po_id}>{po.po_id.slice(0, 8)}</td>
              <td>{po.sku}</td>
              <td>{po.vendor_id}</td>
              <td>{po.quantity}</td>
              <td>${po.unit_price}</td>
              <td>${po.total_price}</td>
              <td>{po.issued_at ? new Date(po.issued_at).toLocaleString() : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </StatusPanel>
  )
}
