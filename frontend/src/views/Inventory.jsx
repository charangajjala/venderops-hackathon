import { usePolling } from "../hooks/usePolling"
import { getInventory } from "../api"
import { StatusPanel } from "../components/StatusPanel"

export function Inventory() {
  const { data, error, loading } = usePolling(getInventory)

  return (
    <StatusPanel loading={loading} error={error} empty={data && data.length === 0} emptyLabel="No inventory items yet.">
      <table>
        <thead>
          <tr>
            <th>SKU</th>
            <th>On hand</th>
            <th>Reorder threshold</th>
            <th>Reorder quantity</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((item) => {
            const low = Number(item.quantity_on_hand) < Number(item.reorder_threshold)
            return (
              <tr key={item.sku} className={low ? "row-alert" : ""}>
                <td>{item.sku}</td>
                <td>{item.quantity_on_hand}</td>
                <td>{item.reorder_threshold}</td>
                <td>{item.reorder_quantity}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </StatusPanel>
  )
}
