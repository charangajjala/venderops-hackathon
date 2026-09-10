import { useState } from "react"
import { Inventory } from "./views/Inventory"
import { Vendors } from "./views/Vendors"
import { Rfqs } from "./views/Rfqs"
import { PurchaseOrders } from "./views/PurchaseOrders"

const TABS = [
  { id: "inventory", label: "Inventory", Component: Inventory },
  { id: "vendors", label: "Vendors", Component: Vendors },
  { id: "rfqs", label: "RFQs", Component: Rfqs },
  { id: "pos", label: "Purchase Orders", Component: PurchaseOrders },
]

export default function App() {
  const [activeTab, setActiveTab] = useState("inventory")
  const Active = TABS.find((t) => t.id === activeTab).Component

  return (
    <div className="app">
      <header>
        <h1>VendorOps</h1>
        <p className="tagline">Autonomous procurement agent — live inventory, vendors, RFQs and purchase orders</p>
      </header>
      <nav>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={tab.id === activeTab ? "tab active" : "tab"}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <main>
        <Active />
      </main>
    </div>
  )
}
