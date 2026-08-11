Let me quickly investigate the codebase to give you accurate answers.

Viewed storage.py:1-218
Viewed layout.html:20-110
Searched for "role_required"
Searched for "role_required"
Viewed layout.html:110-223
Viewed routes.py:245-260
Viewed utils.py:1-17

Here are the clear, direct answers to all three questions:

---

## 1. 📦 How and Where is Data Stored?

**Everything is stored in a single SQLite database file:**

```
📁 vema-main/
  └── instance/
        └── data.db   ← ALL data lives here
```

**How it works — a 3-layer flow:**

```
Form Submit → routes.py → storage.py (in-memory list) → SQLite (data.db)
```

| Layer | Role |
|---|---|
| `models.py` | Python classes (`Vendor`, `Purchase`, `Payment`…) — defines what each object looks like |
| `storage.py` | `SQLiteStorage` class — loads all rows from DB into **in-memory Python lists** on startup, then writes back to SQLite on every save |
| `instance/data.db` | The actual file on disk — persistent storage across restarts |

**Key behavior to know:**
- On every `add_*()` call (e.g. `add_vendor()`), it immediately runs a full `DELETE + INSERT` of that table back to SQLite — so data is always persisted right away
- On startup, it reads all tables into RAM (`self.vendors`, `self.purchases`, etc.) — so all queries happen in Python memory, **not** via SQL queries
- File uploads (invoices, payment proofs) are saved separately in `app/static/uploads/`

---

## 2. 📋 Does it Comply with the PRD?

**Mostly yes — here's the current compliance state:**

| PRD Requirement | Status | Notes |
|---|---|---|
| Vendor Registration (Name, Phone, City, State) | ✅ Done | |
| Contact Person | ✅ Added (this session) | |
| Vendor Type (Manufacturer/Dealer/etc.) | ✅ Added (this session) | |
| Vendor Status (Active/Inactive) | ✅ Added (this session) | |
| Purchase entry (Brand, Model, Qty, Unit Price, Total, Date, Attachment) | ✅ Done | |
| Payment entry (Date, Method, Amount, Attachment) | ✅ Done | |
| Reference Number / Transaction ID | ✅ Added (this session) | |
| Payment Notes/Remarks | ✅ Added (this session) | |
| Outstanding Balance = Purchases − Payments | ✅ Done | Auto-calculated as a property |
| Vendor Detail Page (KPIs, purchase/payment history) | ✅ Done | |
| Dashboard with charts & date filters | ✅ Done | |
| Vendor-wise analytics | ✅ Done | |
| Reports | ✅ Done | |

**⚠️ Gaps still remaining (not yet built):**
| PRD Requirement | Status |
|---|---|
| **Goods Received** module (separate from Purchases) | ❌ Sidebar link exists but points to `/purchases` — no separate GRN page |
| **Invoices** module (separate view) | ❌ Sidebar link exists but points to `/purchases` |
| **Analytics** (separate page from Reports) | ❌ Both sidebar links go to `/reports` |
| Single-vendor **purchase trend chart** (Chart.js) | ⚠️ Partial — exists on vendor detail but basic |

---

## 3. 👤 Do Vendor and Admin See the Same Things?

**Currently — almost yes, with only a small difference:**

| Feature | Admin | Regular User (Staff) |
|---|---|---|
| Dashboard | ✅ Full access | ✅ Full access |
| Vendors (view, add, edit) | ✅ | ✅ |
| **Delete Vendor** | ✅ | ❌ 403 Forbidden |
| Purchases (view, add) | ✅ | ✅ |
| **Delete Purchase** | ✅ | ❌ 403 Forbidden |
| Payments (view, add) | ✅ | ✅ |
| **Delete Payment** | ✅ | ❌ 403 Forbidden |
| Products, Customers, Offers | ✅ | ✅ (most actions) |
| **Users page** | ✅ Visible in sidebar | ❌ Hidden in sidebar |
| **Settings page** | ✅ Visible in sidebar | ❌ Hidden in sidebar |
| **Add/Edit/Delete Users** | ✅ | ❌ 403 Forbidden |
| **Store Settings** | ✅ | ❌ 403 Forbidden |

**In short:** Non-admin users see the same UI **except** Users & Settings are hidden in the sidebar, and all **delete actions** + user management are blocked at the route level with a `403` error. There is **no separate "Vendor" login role** — just `Admin` vs everything else.

> **Suggestion:** If you want a more granular role system (e.g., a read-only "Viewer" who can't add purchases either), that would need new roles added to the DB and more `@role_required` decorators on add/edit routes.