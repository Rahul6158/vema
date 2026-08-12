# Vema Store Manager & Vendor CRM

A modern, high-performance **Flask + SQLite** Vendor Management and Store Operations CRM application. Designed with a clean, responsive interface featuring dynamic data visualizations, multi-period financial analytics, automated WhatsApp messaging, and comprehensive accounts payable management.

---

## 🚀 Key Features Overview

- **360° Vendor Management**: Full supplier profiles, credit limit tracking, ledger statements, and payment settlement histories.
- **Purchase Order System**: Complete PO workflow from draft creation to approval, delivery tracking, and GRN inventory updates.
- **Accounts Payable & Payments**: Log partial or full vendor settlements across UPI, Bank Transfer, Cash, and Cheque modes.
- **Inventory & Stock Management**: Product catalog with SKU tracking, stock levels, reorder alerts, and Goods Received Notes (GRN).
- **Invoices & Customer CRM**: Manage customer directory, sales invoices, and promotional broadcasts.
- **Reports & Aging Analytics**: Deep financial analytics, 30/60/90-day aging reports, and CSV data exports.
- **Dynamic Enlargeable Charts**: Interactive Chart.js visual graphics with blurred-backdrop zoom modals, doughnut center text overlays, and detailed legends.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, Flask, Flask-Login, Flask-SQLAlchemy (SQLite)
- **Frontend**: HTML5, Vanilla JS, Bootstrap 5, Custom Vanilla CSS (Design Tokens & Glassmorphism)
- **Visualization**: Chart.js 4.x
- **Data Engine**: SQLite (`instance/data.db`) with JSON storage abstraction layer
- **Deployment**: Compatible with Gunicorn, PythonAnywhere, Vercel, and standard Linux VPS

---

## ⚡ Quick Start & Setup

### 1. Clone & Environment Setup

```bash
git clone https://github.com/Rahul6158/vema.git
cd vema
python -m venv venv
```

Activate virtual environment:
- **Windows**: `venv\Scripts\activate`
- **Linux/macOS**: `source venv/bin/activate`

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and set your configuration parameters:

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secure-random-secret-key
```

### 4. Run Application

```bash
python run.py
```

Open `http://127.0.0.1:5000` in your web browser. Default administrator credentials are generated upon initial database seeding.

---

## 📖 Detailed Page-by-Page Capabilities

Below is a comprehensive guide to every page available in the Vema application, detailing its purpose, functionality, and capabilities.

---

### 1. Dashboard (`/`)
The primary operational hub providing high-level financial metrics, interactive charts, and recent transaction logs.

- **KPI Cards**: Real-time totals for **Total Purchases (₹)**, **Total Settled Payments (₹)**, **Net Outstanding Dues (₹)**, and **Active Vendor Count**, complete with percentage trend indicators comparing current vs. previous periods.
- **Dynamic Scoping & Filters**: Filter all dashboard KPIs, charts, and recent tables by:
  - Time Periods: *Today, This Week, This Month, This Quarter, This Year, or Custom Date Range*.
  - Vendor Filter: Scope all metrics to a specific vendor.
- **Interactive Visual Charts**:
  - **Purchases by Vendor**: Bar chart showing top vendors by purchase volume. Includes an **Enlarge Graph** button to zoom into full screen.
  - **Payments by Vendor**: Donut chart featuring a center text overlay (`₹ Total Settled`) and a custom breakdown legend displaying amounts and percentage shares.
- **At-a-Glance Activity Tables**:
  - **Recent Purchase Orders**: Displays PO Number, Vendor Name, Date, Amount, and color-coded Status Badges (`Approved`, `Pending`, `Delivered`, `Draft`).
  - **Recent Payments**: Displays Payment Reference Number, Vendor Name, Date, Amount Paid, and Payment Mode.

---

### 2. Vendor Directory (`/vendors`)
Manage all supplier relationships, contact details, and financial standing in one centralized list.

- **Capabilities**:
  - Search vendors by name, phone number, GSTIN, or city.
  - Displays contact person, phone, email, state/city, credit period, credit limit, and current **Outstanding Balance**.
  - Direct links to **View Profile**, **View Ledger**, or **Edit Vendor**.
  - Quick action to add new vendors.

---

### 3. Add / Edit Vendor (`/vendors/add`, `/vendors/<id>/edit`)
Forms for registering new vendors or modifying existing details.

- **Fields**: Vendor Name, Contact Person Name, Email, Phone Number, Secondary Phone, GSTIN, Address, City, State, Pincode, Credit Limit (₹), Credit Period (Days), and Notes.
- **Validation**: Automatic validation for duplicate vendor names and formatted phone/GST numbers.

---

### 4. Vendor 360° Profile (`/vendors/<id>`)
A detailed 360-degree overview of a single vendor’s complete operational relationship.

- **Summary Cards**: Displays Vendor Outstanding Balance, Total Purchased Value, and Total Settled Payments.
- **Vendor Specific Charts**:
  - **Purchase vs Payment Trend**: Interactive line chart showing purchase activity vs settlement history over time.
  - **Payment Mix**: Donut chart detailing payment methods used for this vendor (Cash, UPI, Bank Transfer, Cheque).
- **Tabbed History Views**:
  - **Purchase Orders Tab**: List of all POs associated with this vendor with status badges and quick view links.
  - **Payment History Tab**: Log of all payments disbursed to this vendor with reference numbers and proof documents.
  - **Vendor Details Tab**: Complete address, GSTIN, credit limits, and contact info.

---

### 5. Vendor Ledger Statement (`/vendors/<id>/ledger`)
An accounting-grade financial ledger detailing every debit and credit transaction.

- **Capabilities**:
  - Chronological statement listing all Purchase Orders (Debits) and Payments (Credits).
  - Calculates a real-time **Running Balance** after every entry.
  - Printer-friendly and export-ready view for accounting reconciliation.

---

### 6. Purchase Orders Directory (`/purchases`)
Comprehensive registry of all Purchase Orders (POs) issued to suppliers.

- **Capabilities**:
  - Paginated table showing PO ID, Vendor, Date, Item Count, Net Amount, Tax Amount, Total Amount, and Status.
  - Filter POs by Status (`Draft`, `Pending`, `Approved`, `Delivered`, `Cancelled`) or search by PO ID / Vendor.
  - Summary metrics at the top: Total PO Count, Total Purchase Amount, and Pending POs.
  - Quick button to **Create New Purchase Order**.

---

### 7. Create Purchase Order (`/purchases/add`)
A form to issue new purchase orders to vendors.

- **Capabilities**:
  - Select Vendor, PO Date, Expected Delivery Date, and PO Status.
  - Itemization: Select Brand, Model, Product Name, Quantity, Unit Price, Discount, and Tax/GST rate.
  - File Attachment: Upload vendor invoices, quotes, or delivery notes (PDF, JPG, PNG).
  - **WhatsApp Alert Option**: Checkbox to automatically send a purchase order notification directly to the supplier's WhatsApp number.

---

### 8. View Purchase Order (`/purchases/<id>`)
Detailed breakdown view of a specific Purchase Order.

- **Capabilities**:
  - View PO details, vendor info, delivery status, and attached documents.
  - Itemized table with unit prices, GST breakdown, subtotal, and grand total.
  - Direct action button to trigger a **WhatsApp Order Notification** to the vendor.

---

### 9. Payments Directory (`/payments`)
Central log of all financial disbursements made to vendors.

- **Capabilities**:
  - Paginated list showing Reference Number, Vendor Name, Payment Date, Amount Paid (₹), Payment Mode (UPI, Bank Transfer, Cash, Cheque, NEFT), and Attached Receipt Proof.
  - Search by reference number or filter by payment method.
  - Quick action to **Record New Payment**.

---

### 10. Record New Payment (`/payments/add`)
Interface for logging vendor settlements against outstanding balances.

- **Capabilities**:
  - Select Vendor (displays current outstanding balance dynamically).
  - Enter Payment Date, Amount Paid (₹), Payment Method, Reference/UTR Number, and Notes.
  - Upload Payment Proof receipt (bank transfer receipt screenshot, cheque image, etc.).
  - Auto-updates the vendor’s outstanding balance in real time upon submission.

---

### 11. View Payment Receipt (`/payments/<id>`)
Dedicated receipt view for a specific payment transaction.

- **Capabilities**:
  - Displays payment voucher details, vendor info, payment method, reference number, and exact time recorded.
  - Preview attached payment proof documents/images directly on page.
  - Link to view updated vendor ledger.

---

### 12. Goods Received Notes - GRN (`/grn`, `/grn/add`)
Track physical inventory arrival against Purchase Orders.

- **Capabilities**:
  - **GRN List (`/grn`)**: View all received stock shipments, linked PO numbers, delivery dates, received quantities, and receiving officer.
  - **Create GRN (`/grn/add`)**: Match incoming delivery against an approved PO, record accepted vs rejected/damaged items, record delivery challan number, and auto-increment product stock levels.

---

### 13. Sales Invoices (`/invoices`, `/invoices/<id>`)
Customer billing and sales invoice management.

- **Capabilities**:
  - **Invoices Directory (`/invoices`)**: List customer invoices with invoice number, customer name, date, total amount, payment status (`Paid`, `Unpaid`, `Partial`), and due date.
  - **Printable Invoice (`/invoices/<id>`)**: Clean, printable invoice template formatted with store logo, tax details (GSTIN), itemized products, terms & conditions, and payment breakdown.

---

### 14. Products & Stock Inventory (`/products`, `/products/add`, `/products/<id>/edit`)
Product catalog and inventory control.

- **Capabilities**:
  - **Product Catalog (`/products`)**: Table displaying SKU, Product Name, Brand, Category, Unit Purchase Price, Selling Price, In-Stock Quantity, and Stock Status (`In Stock`, `Low Stock`, `Out of Stock`).
  - **Add/Edit Product**: Manage product metadata, category, brand, reorder threshold alerts, and pricing.

---

### 15. Customer Directory (`/customers`, `/customers/add`, `/customers/<id>/edit`)
Client CRM database.

- **Capabilities**:
  - Manage retail and wholesale customer profiles, phone numbers, email, address, and purchase histories.
  - Direct WhatsApp shortcut button to send promotional offers or updates to customers.

---

### 16. Promotional Offers & WhatsApp Broadcast (`/offers`, `/offers/add`)
Marketing campaigns and announcement broadcasts.

- **Capabilities**:
  - Create promotional offers, discount banners, or store announcements.
  - Broadcast offer details directly to selected customers or suppliers via WhatsApp API integration.

---

### 17. General Business Reports (`/reports`)
Comprehensive visual intelligence and financial analytics.

- **Reports Breakdown**:
  - **Purchase Trend**: Line/bar chart showing purchase volume trends over recent months.
  - **Payments by Method**: Donut chart showing share of payments made via UPI, Cash, Cheque, and Bank Transfer.
  - **Top Vendors by Volume**: Bar chart identifying top suppliers by expenditure.

---

### 18. Accounts Payable Aging Report (`/reports/aging`)
Critical risk-management tool for tracking overdue vendor payments.

- **Capabilities**:
  - Categorizes unpaid vendor balances into aging buckets:
    - **Current (0-30 Days)**
    - **31 - 60 Days**
    - **61 - 90 Days**
    - **90+ Days Overdue**
  - Displays total exposure per aging category to help prioritize payment disbursements.

---

### 19. Monthly Cumulative Analytics (`/analytics`)
Multi-period performance comparison.

- **Capabilities**:
  - Comparative bar chart charting monthly purchases vs payments over time.
  - Calculates monthly variance, settlement ratios, and growth metrics.

---

### 20. User Management & Access Control (`/users`, `/users/add`, `/users/<id>/edit`)
Staff management and role-based permissions.

- **Capabilities**:
  - Manage user accounts (Admin, Manager, Staff).
  - Enforce role-based permission checks across sensitive routes (e.g. deleting records or editing settings).

---

### 21. User Profile & Password (`/profile`, `/change-password`)
Self-service user settings.

- **Capabilities**:
  - Update personal profile details (Name, Email, Phone).
  - Securely change login password with current password verification.

---

### 22. Store Settings (`/settings`)
Global application configuration.

- **Capabilities**:
  - Configure Store Name, Tagline, Phone, Email, Address, GSTIN number.
  - Upload Store Logo (used across navigation bar and printable invoices).
  - Set default currency symbol (`₹`) and operational defaults.

---

## 🗄️ Database Architecture

The application utilizes **SQLite** (`instance/data.db`) managed via SQLAlchemy models with a storage abstraction layer (`app/storage.py`):

- `vendors`: Supplier master records & credit tracking.
- `purchases` & `purchase_items`: PO headers and line items.
- `payments`: Vendor payment transactions and receipt uploads.
- `goods_received`: Inventory stock arrival receipts.
- `products`, `brands`, `categories`: Stock catalog.
- `customers`, `invoices`: Sales & client billing records.
- `users`, `roles`: Authentication & permissions.
- `offers`, `whatsapp_messages`: Marketing & messaging logs.

---

## 🚀 Deployment Instructions

### PythonAnywhere Deployment
1. Upload code repository or clone via SSH.
2. Setup virtualenv and install dependencies: `pip install -r requirements.txt`.
3. Use `deploy_pythonanywhere.py` script or configure Web WSGI file using `pythonanywhere_wsgi.py.example`.

### Vercel Serverless Deployment
- Configured via `vercel.json` for serverless deployment using WSGI handler.

---

## 📄 License & Credits

Built for **Vema Store Manager**. All rights reserved.
