import { Search } from "lucide-react";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useAppStore } from "../store/appStore";

interface CustomerSelectProps {
  value: number | null;
  onChange: (customerId: number | null) => void;
}

export function CustomerSelect({ value, onChange }: CustomerSelectProps) {
  const { customers, loadCustomers } = useAppStore();
  const [query, setQuery] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => loadCustomers(50, 0), 250);
    return () => window.clearTimeout(timer);
  }, [loadCustomers, query]);

  const filtered = useMemo(() => {
    const normalized = query.toLowerCase();
    return customers.filter(
      (customer) =>
        customer.full_name.toLowerCase().includes(normalized) ||
        customer.customer_code.toLowerCase().includes(normalized) ||
        String(customer.id).includes(normalized)
    );
  }, [customers, query]);

  function handleSelect(event: ChangeEvent<HTMLSelectElement>) {
    onChange(event.target.value ? Number(event.target.value) : null);
  }

  return (
    <div className="field">
      <label htmlFor="customer-search">Customer lookup</label>
      <div className="search-row">
        <Search aria-hidden="true" />
        <input
          id="customer-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by name, ID, or code"
        />
      </div>
      <select aria-label="Select customer" value={value ?? ""} onChange={handleSelect}>
        <option value="">Manual entry / no customer selected</option>
        {filtered.map((customer) => (
          <option key={customer.id} value={customer.id}>
            {customer.full_name} · {customer.customer_code}
          </option>
        ))}
      </select>
    </div>
  );
}
