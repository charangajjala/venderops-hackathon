import { usePolling } from "../hooks/usePolling"
import { getVendors } from "../api"
import { StatusPanel } from "../components/StatusPanel"

export function Vendors() {
  const { data, error, loading } = usePolling(getVendors)

  return (
    <StatusPanel loading={loading} error={error} empty={data && data.length === 0} emptyLabel="No vendors onboarded yet.">
      <table>
        <thead>
          <tr>
            <th>Vendor</th>
            <th>Contact</th>
            <th>Status</th>
            <th>Trusted</th>
            <th>Reliability</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((v) => (
            <tr key={v.vendor_id}>
              <td>{v.name ?? v.vendor_id}</td>
              <td>{v.contact_email}</td>
              <td>{v.onboarding_status}</td>
              <td>{v.trusted ? "yes" : "no"}</td>
              <td>{v.reliability_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </StatusPanel>
  )
}
