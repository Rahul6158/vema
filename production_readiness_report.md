# VEMA — Production Readiness Gap Analysis
### vs. Vendor Management CRM PRD

---

> [!IMPORTANT]
> Changes are grouped by **Priority**: P0 = blocker (app breaks or data is wrong), P1 = core PRD feature missing, P2 = UX/quality gap, P3 = nice-to-have.

---

## P0 — Critical / Blockers

### 1. Dashboard Filters Are Static (Not Wired to Backend)
**File:** `dashboard.html` L9–28
- The "Vendor Scope" dropdown and "Time Period" select do **nothing** — they have no `name` attribute and are not inside a `<form>`, so changing them does not reload the page or filter any data.
- The filter logic **is** implemented in `routes.py` (line 46–88) but the UI doesn't send the params.
- **Fix:** Wrap the filter bar in a `<form method="GET">`, add `name="vendor_id"` and `name="filter"` to the selects, and use `onchange="this.form.submit()"`.

### 2. KPI Trend Numbers Are Hardcoded Fake Data
**File:** `dashboard.html` L48, 68
- `↑ 12 this month` and `↑ 8.5% this month` are **hardcoded strings** — they never change based on real data.
- **Fix:** Calculate month-over-month change in `routes.py` and pass as template variables.

### 3. `view_purchase.html` and `view_payment.html` — No Reference Number / Notes Displayed
**Files:** `view_payment.html`, `view_purchase.html`
- The new `reference_number` and `notes` fields we added to the model are **not shown** on the detail view pages.
- **Fix:** Add those fields to both view templates.

### 4. Vendor Detail Page Does Not Show `contact_person`, `vendor_type`, `status`
**File:** `vendor_detail.html` L12–15
- Shows only Phone and Location. The new PRD fields (`Contact Person`, `Vendor Type`, `Status`) are stored but never displayed on the profile.
- **Fix:** Add these fields to the vendor profile header card.

### 5. Payment History Missing `reference_number` Column
**File:** `vendor_detail.html` L136–141
- The payment table on the vendor detail page only shows: Date, Method, Amount, Proof. The `reference_number` column is missing.
- **Fix:** Add a Reference No. column to the payment history table.

---

## P1 — Core PRD Features Missing

### 6. Goods Received Note (GRN) Module — Not Built
**PRD Section:** Purchase/Inventory Management
- The sidebar has a "Goods Received" link but it just redirects to `/purchases`.
- A GRN is a separate concept: it confirms physical receipt of goods after a purchase order is raised.
- **Fix needed:** New route `/grn`, model `GoodsReceived` with fields: `purchase_id`, `received_date`, `received_qty`, `condition_notes`, `received_by`. New template `grn_list.html` + `new_grn.html`.

### 7. Invoice / Proforma Invoice Module — Not Built
**PRD Section:** Invoice Management
- The sidebar has "Invoices" link pointing to `/purchases`. There is a `invoice.html` template (1.4KB) but it is just a basic stub.
- **Fix needed:** Proper invoice view/print route linked from each purchase, with an invoice number, vendor details, line items, totals, payment summary, and a print/PDF button.

### 8. Analytics Page — Duplicate of Reports (Not a Separate Module)
**File:** `layout.html` L74–77
- Both "Reports" and "Analytics" sidebar links go to `/reports`.
- **Fix:** Either merge into one nav item, or build a separate `/analytics` page with advanced charts (vendor comparison, category breakdown, monthly trend comparison across all vendors).

### 9. No Export to PDF / Excel
**PRD Section:** Reporting
- The "Export" button on the dashboard links to `/reports` — it does NOT generate any file download.
- Reports page has no export functionality at all.
- **Fix:** Add `/reports/export?format=csv` route that streams a CSV using Python's `csv` module. Optionally add `xhtml2pdf` or `weasyprint` for PDF.

### 10. No WhatsApp Notification to Vendor
**PRD + `updates_tobe_made.md`**
- PRD requires ability to send WhatsApp messages to vendors (payment reminders, purchase confirmations).
- The model has `WhatsAppMessage` but it's wired only to customers.
- **Fix:** Add a "Send WhatsApp Reminder" button on the Vendor Detail page → route calls Twilio/360Dialog/WhatsApp Business API with a template message including the outstanding balance.

### 11. Role System is Too Coarse (Admin vs. Everyone Else)
**PRD Section:** User Management
- The PRD specifies distinct roles. Currently there are only 2 effective roles: `Admin` (can delete) and everything else (cannot delete).
- Non-admin users can still add/edit vendors, purchases, and payments — which may not be desired.
- **Fix:** Add roles `Manager` (add/edit, no delete), `Accountant` (payments only), `Viewer` (read-only). Add `@role_required` decorators appropriately.

### 12. No Ledger / Statement View per Vendor
**PRD Section:** Balance & Ledger
- The PRD requires a **chronological ledger** — a single combined timeline of Purchases (Dr) and Payments (Cr) with a running balance column per vendor.
- Currently purchases and payments are in separate tables on the vendor detail page.
- **Fix:** A new `/vendors/<id>/ledger` route that merges and sorts both lists by date, and shows a running `Running Balance` column.

### 13. No Overdue Payment Alerts / Aging Report
**PRD Section:** Reporting
- No concept of "payment due date" or aging buckets (0–30 days, 31–60 days, 60+ days overdue).
- **Fix:** Add `due_date` to Purchase model. Build an aging report route `/reports/aging` showing which vendor balances are overdue.

---

## P2 — UX / Quality Gaps

### 14. Vendor Form Missing Address Line / GST Fields
**File:** `vendor_form.html`
- PRD likely expects: **GST Number**, **PAN**, **Bank Account / IFSC** for vendor payments.
- Currently only Name, Phone, City, State, Contact Person, Type, Status.
- **Fix:** Add `gst_number`, `pan_number`, `bank_account`, `ifsc_code` to Vendor model + form + DB migration.

### 15. Purchase Form — No Multi-Item Line Entry
**File:** `new_purchase.html`
- A real purchase order often has **multiple product lines** (e.g., 5 ACs + 3 Fridges in one PO).
- Currently only 1 product per purchase. The `PurchaseItem` model exists but is unused in the form.
- **Fix:** Add a dynamic "Add Line Item" JS row in `new_purchase.html` that submits multiple products as `items[0][brand]`, `items[0][qty]`… and parse them in the route.

### 16. Dashboard Vendor Filter & Time Filter Have No "Apply" Button on Mobile
**File:** `dashboard.html`
- On small screens, the filter bar collapses, but there's no submit button — relies on `onchange`. If JS is slow, no filter applies.
- **Fix:** Add a visible "Apply" button next to the filter row.

### 17. Payments Page — No Reference Number Column in Table
**File:** `payments.html`
- The new `reference_number` field is not shown in the payments listing table.
- **Fix:** Add Reference No. column.

### 18. Vendor Detail — No "Edit" Button for Individual Purchases/Payments
**File:** `vendor_detail.html`
- Users can add but cannot edit an existing purchase or payment record — only Admins can delete.
- **Fix:** Add `edit_purchase` and `edit_payment` routes and link buttons in the detail tables.

### 19. Sidebar Nav Items "Goods Received", "Invoices", "Analytics" Point to Wrong URLs
**File:** `layout.html` L49–57, L74–77
- These three links are placeholders. Until the real pages are built (P1 items above), they should at least show a "Coming Soon" page, not silently load the wrong page.
- **Fix (quick):** Create a simple `/coming-soon` route and redirect these links there with a toast message.

### 20. No Pagination on Large Tables
**Files:** `vendors.html`, `purchases.html`, `payments.html`
- All records are loaded into the page at once. With 500+ records this becomes slow and unusable.
- **Fix:** Add server-side pagination (`?page=1&per_page=25`) or use a JS datatable library.

### 21. Storage Layer: `_save_collection` Does Full DELETE + INSERT Every Write
**File:** `storage.py` L128
- Every time a single payment is added, the **entire payment table** is deleted and rewritten. This is fine for small data but will fail under concurrent users or large datasets.
- **Fix for production:** Switch to proper ORM (SQLAlchemy) with individual `INSERT/UPDATE/DELETE` per record. Or at minimum add a `conn.isolation_level` check.

### 22. No Input Validation / Flash Error Messages on Forms
**Files:** All form templates
- Only `vendor_name` is validated server-side. Fields like `phone`, `amount_paid`, `purchase_date` have no server-side validation — only browser-level `required` attributes.
- **Fix:** Add `wtforms` or manual validation with descriptive flash messages for every field.

---

## P3 — Polish / Production Infrastructure

### 23. `SECRET_KEY` Must Be Set from Environment Variable
**File:** `app/__init__.py` or `config.py`
- If the secret key is hardcoded, it's a security risk in production.
- **Fix:** `app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-fallback-key')`.

### 24. No HTTPS / Security Headers
- Missing `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options` headers.
- **Fix:** Add `flask-talisman` or set headers in a `@app.after_request` hook.

### 25. File Upload Has No Size Limit or Type Validation
**File:** `routes.py` `save_attachment()`
- No `MAX_CONTENT_LENGTH` is set. Users can upload any file of any size.
- **Fix:** Add `app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024` (10MB). Validate extension in `save_attachment()`.

### 26. No Database Backup Mechanism
- `data.db` is a single file with no automated backup.
- **Fix:** Add a `/admin/backup` route that streams a copy of `data.db` as a download. Schedule a daily backup using cron/task scheduler.

### 27. Notification Bell Shows Static "3" Badge
**File:** `layout.html` L137
- The bell icon always shows `3` — it's hardcoded. It never reflects real notifications.
- **Fix:** Implement a basic notification model (overdue payments, new vendor added) and count them dynamically.

### 28. Login Page Has "Forgot Password" Link That Goes Nowhere Useful
**File:** `forgot_password.html` (1KB stub)
- The forgot password form exists but presumably doesn't send an email.
- **Fix:** Integrate Flask-Mail + token-based reset, or disable the link until implemented.

---

## Summary Table

| # | Change | Priority | Files Affected |
|---|---|---|---|
| 1 | Wire dashboard filter dropdowns to backend | **P0** | `dashboard.html` |
| 2 | Replace hardcoded KPI trend numbers | **P0** | `dashboard.html`, `routes.py` |
| 3 | Show `reference_number`/`notes` in view templates | **P0** | `view_payment.html`, `view_purchase.html` |
| 4 | Show new vendor fields on vendor detail | **P0** | `vendor_detail.html` |
| 5 | Add reference_number column to payment table | **P0** | `vendor_detail.html`, `payments.html` |
| 6 | Build Goods Received Note (GRN) module | **P1** | New route + model + 2 templates |
| 7 | Build proper Invoice view + print | **P1** | `invoice.html`, `routes.py` |
| 8 | Fix Analytics sidebar (separate page or merge) | **P1** | `layout.html` |
| 9 | Add CSV/PDF Export from Reports page | **P1** | `routes.py`, `reports.html` |
| 10 | WhatsApp notification to vendor | **P1** | `routes.py`, `vendor_detail.html` |
| 11 | Multi-role system (Manager, Accountant, Viewer) | **P1** | `utils.py`, `routes.py`, `layout.html` |
| 12 | Vendor Ledger / Statement page | **P1** | New route + template |
| 13 | Overdue/Aging report | **P1** | `routes.py`, `reports.html` |
| 14 | Add GST, PAN, Bank fields to Vendor | **P2** | `vendor_form.html`, `models.py`, `storage.py` |
| 15 | Multi-item line entry on Purchase form | **P2** | `new_purchase.html`, `routes.py` |
| 16 | Dashboard mobile filter "Apply" button | **P2** | `dashboard.html` |
| 17 | Reference number column in Payments list | **P2** | `payments.html` |
| 18 | Edit Purchase / Edit Payment buttons | **P2** | `vendor_detail.html`, `routes.py` |
| 19 | Fix broken sidebar nav links | **P2** | `layout.html` |
| 20 | Pagination on all listing tables | **P2** | All list templates + `routes.py` |
| 21 | Fix storage layer full-table rewrite | **P2** | `storage.py` |
| 22 | Server-side form validation | **P2** | All form routes |
| 23 | `SECRET_KEY` from env variable | **P3** | `__init__.py` / config |
| 24 | HTTPS / security headers | **P3** | `__init__.py` |
| 25 | File upload size + type validation | **P3** | `routes.py` |
| 26 | Database backup route | **P3** | `routes.py` |
| 27 | Dynamic notification bell | **P3** | `layout.html`, `routes.py` |
| 28 | Working forgot-password flow | **P3** | `routes.py`, email config |
