const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ""
const WRITE_API_KEY = import.meta.env.VITE_WRITE_API_KEY ?? ""

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error ?? `request to ${path} failed with ${res.status}`)
  }
  return res.json()
}

export const getInventory = () => request("/inventory")
export const getVendors = () => request("/vendors")
export const getRfqs = () => request("/rfqs")
export const getPurchaseOrders = () => request("/purchase-orders")

export const adjustInventory = (sku, delta) =>
  request(`/inventory/${encodeURIComponent(sku)}/adjust`, {
    method: "POST",
    headers: { "X-Api-Key": WRITE_API_KEY },
    body: JSON.stringify({ delta }),
  })

export const approveRfq = (rfqId) =>
  request(`/rfqs/${rfqId}/approve`, {
    method: "POST",
    headers: { "X-Api-Key": WRITE_API_KEY },
  })

export const rejectRfq = (rfqId) =>
  request(`/rfqs/${rfqId}/reject`, {
    method: "POST",
    headers: { "X-Api-Key": WRITE_API_KEY },
  })
