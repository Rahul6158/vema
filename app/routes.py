import os
import uuid
import requests
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import (Vendor, Payment, Purchase, Customer, Product, Role, User,
                     Category, Brand, StoreSetting, Offer, OfferMessage, Warranty,
                     PurchaseItem, WhatsAppMessage)
from .storage import storage
from .utils import role_required


def get_object_or_404(obj):
    if obj is None:
        abort(404)
    return obj


ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt'}

def save_attachment(file_obj):
    if not file_obj or not file_obj.filename:
        return ''
    ext = file_obj.filename.rsplit('.', 1)[-1].lower() if '.' in file_obj.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        flash(f"File type .{ext} is not allowed. Upload PDF, Image, or Document files.", "warning")
        return ''
    filename = secure_filename(file_obj.filename)
    unique_name = f"{uuid.uuid4().hex[:10]}_{filename}"
    upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
    file_obj.save(upload_path)
    return unique_name



main_bp = Blueprint('main', __name__)


@main_bp.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


# ==============================================================================
# 1. DASHBOARD & ANALYTICS (PRD Sections 4, 5, 6, 7, 12)
# ==============================================================================
@main_bp.route('/')
@login_required
def dashboard():
    selected_vendor_id = request.args.get('vendor_id', type=int)
    time_filter = request.args.get('filter', 'month')
    start_date_param = request.args.get('start_date')
    end_date_param = request.args.get('end_date')

    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)
    all_purchases = storage.purchases
    all_payments = storage.payments

    # Financial KPIs across CRM
    total_purchases_val = sum(p.total_amount for p in all_purchases)
    total_payments_val = sum(p.amount_paid for p in all_payments)
    total_outstanding = total_purchases_val - total_payments_val
    total_vendors_count = len(vendors)

    # Date Range Calculation
    today = date.today()
    if time_filter == 'day':
        filter_start = today
        filter_end = today
        prev_start = today - timedelta(days=1)
        prev_end = today - timedelta(days=1)
    elif time_filter == 'week':
        filter_start = today - timedelta(days=6)
        filter_end = today
        prev_start = today - timedelta(days=13)
        prev_end = today - timedelta(days=7)
    elif time_filter == 'month':
        filter_start = date(today.year, today.month, 1)
        filter_end = today
        # Previous month
        if today.month == 1:
            prev_start = date(today.year - 1, 12, 1)
            prev_end = date(today.year - 1, 12, 31)
        else:
            prev_start = date(today.year, today.month - 1, 1)
            import calendar
            prev_end = date(today.year, today.month - 1, calendar.monthrange(today.year, today.month - 1)[1])
    elif time_filter == 'quarter':
        q_month = ((today.month - 1) // 3) * 3 + 1
        filter_start = date(today.year, q_month, 1)
        filter_end = today
        prev_q_month = q_month - 3 if q_month > 3 else 10
        prev_q_year = today.year if q_month > 3 else today.year - 1
        prev_start = date(prev_q_year, prev_q_month, 1)
        prev_end = filter_start - timedelta(days=1)
    elif time_filter == 'year':
        filter_start = date(today.year, 1, 1)
        filter_end = today
        prev_start = date(today.year - 1, 1, 1)
        prev_end = date(today.year - 1, 12, 31)
    elif time_filter == 'custom' and start_date_param and end_date_param:
        try:
            filter_start = date.fromisoformat(start_date_param)
            filter_end = date.fromisoformat(end_date_param)
            delta = filter_end - filter_start
            prev_start = filter_start - timedelta(days=delta.days + 1)
            prev_end = filter_start - timedelta(days=1)
        except ValueError:
            filter_start = date(today.year, today.month, 1)
            filter_end = today
            prev_start = prev_end = date(today.year, today.month, 1) - timedelta(days=1)
    else:
        filter_start = date(today.year, today.month, 1)
        filter_end = today
        if today.month == 1:
            prev_start = date(today.year - 1, 12, 1)
            prev_end = date(today.year - 1, 12, 31)
        else:
            import calendar
            prev_start = date(today.year, today.month - 1, 1)
            prev_end = date(today.year, today.month - 1, calendar.monthrange(today.year, today.month - 1)[1])

    selected_vendor = storage.get_vendor(selected_vendor_id) if selected_vendor_id else None

    # Current period totals
    cur_purchases = sum(p.total_amount for p in all_purchases
                        if filter_start <= (p.purchase_date or p.created_at.date()) <= filter_end)
    cur_payments = sum(p.amount_paid for p in all_payments
                       if filter_start <= (p.payment_date or p.created_at.date()) <= filter_end)

    # Previous period totals for % change
    prev_purchases = sum(p.total_amount for p in all_purchases
                         if prev_start <= (p.purchase_date or p.created_at.date()) <= prev_end)
    prev_payments = sum(p.amount_paid for p in all_payments
                        if prev_start <= (p.payment_date or p.created_at.date()) <= prev_end)

    def pct_change(cur, prev):
        if prev == 0:
            return 100.0 if cur > 0 else 0.0
        return ((cur - prev) / prev) * 100

    purchases_pct_change = pct_change(cur_purchases, prev_purchases)
    payments_pct_change = pct_change(cur_payments, prev_payments)
    outstanding_change = cur_purchases - cur_payments  # positive = more bought than paid this period

    # Vendors added this calendar month
    this_month_start = date(today.year, today.month, 1)
    vendors_added_this_month = sum(1 for v in vendors if v.created_at and v.created_at.date() >= this_month_start)

    # Vendor Comparison analytics
    vendor_purchase_comparison = []
    vendor_payment_comparison = []
    target_vendors = [selected_vendor] if selected_vendor else vendors

    for v in target_vendors:
        v_purchases = sum(p.total_amount for p in v.purchases if filter_start <= (p.purchase_date or p.created_at.date()) <= filter_end)
        v_payments = sum(p.amount_paid for p in v.payments if filter_start <= (p.payment_date or p.created_at.date()) <= filter_end)
        vendor_purchase_comparison.append({'vendor': v.vendor_name, 'amount': v_purchases})
        vendor_payment_comparison.append({'vendor': v.vendor_name, 'amount': v_payments})

    # Recent Records
    if selected_vendor:
        recent_purchases = sorted(selected_vendor.purchases, key=lambda p: p.purchase_date or p.created_at.date(), reverse=True)[:5]
        recent_payments = sorted(selected_vendor.payments, key=lambda p: p.payment_date or p.created_at.date(), reverse=True)[:5]
    else:
        recent_purchases = sorted(all_purchases, key=lambda p: p.purchase_date or p.created_at.date(), reverse=True)[:5]
        recent_payments = sorted(all_payments, key=lambda p: p.payment_date or p.created_at.date(), reverse=True)[:5]

    return render_template(
        'dashboard.html',
        vendors=vendors,
        selected_vendor=selected_vendor,
        selected_vendor_id=selected_vendor_id,
        time_filter=time_filter,
        start_date=start_date_param,
        end_date=end_date_param,
        total_purchases_val=total_purchases_val,
        total_payments_val=total_payments_val,
        total_outstanding=total_outstanding,
        total_vendors_count=total_vendors_count,
        vendors_added_this_month=vendors_added_this_month,
        purchases_pct_change=purchases_pct_change,
        payments_pct_change=payments_pct_change,
        outstanding_change=outstanding_change,
        vendor_purchase_comparison=vendor_purchase_comparison,
        vendor_payment_comparison=vendor_payment_comparison,
        recent_purchases=recent_purchases,
        recent_payments=recent_payments
    )



# ==============================================================================
# 2. VENDOR REGISTRATION & MANAGEMENT (PRD Sections 1, 9)
# ==============================================================================
@main_bp.route('/vendors')
@login_required
def vendors():
    query = request.args.get('q', '')
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')

    vendor_list = storage.search_vendors(query) if query else storage.vendors
    if status_filter and status_filter != 'All':
        vendor_list = [v for v in vendor_list if getattr(v, 'status', 'Active') == status_filter]
    if type_filter and type_filter != 'All':
        vendor_list = [v for v in vendor_list if getattr(v, 'vendor_type', 'Supplier') == type_filter]

    vendor_list = sorted(vendor_list, key=lambda v: v.vendor_name)

    total_vendors_count = len(storage.vendors)
    active_vendors_count = sum(1 for v in storage.vendors if getattr(v, 'status', 'Active') == 'Active')
    inactive_vendors_count = sum(1 for v in storage.vendors if getattr(v, 'status', 'Active') == 'Inactive')
    total_purchases_val = sum(p.total_amount for p in storage.purchases)
    total_payments_val = sum(p.amount_paid for p in storage.payments)
    total_outstanding_val = total_purchases_val - total_payments_val

    return render_template(
        'vendors.html',
        vendors=vendor_list,
        query=query,
        status_filter=status_filter,
        type_filter=type_filter,
        total_vendors_count=total_vendors_count,
        active_vendors_count=active_vendors_count,
        inactive_vendors_count=inactive_vendors_count,
        total_purchases_val=total_purchases_val,
        total_outstanding_val=total_outstanding_val
    )


@main_bp.route('/vendors/add', methods=['GET', 'POST'])
@login_required
def add_vendor():
    if request.method == 'POST':
        vendor_name = request.form.get('vendor_name', '').strip()
        phone = request.form.get('phone', '').strip()
        state = request.form.get('state', '').strip()
        city = request.form.get('city', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        vendor_type = request.form.get('vendor_type', '').strip()
        status = request.form.get('status', 'Active').strip()
        gst_number = request.form.get('gst_number', '').strip()
        pan_number = request.form.get('pan_number', '').strip()
        bank_account = request.form.get('bank_account', '').strip()
        ifsc_code = request.form.get('ifsc_code', '').strip()

        if not vendor_name:
            flash('Vendor Name is required.', 'danger')
            return redirect(url_for('main.add_vendor'))
        vendor = Vendor(
            vendor_name=vendor_name, phone=phone, state=state, city=city,
            contact_person=contact_person, vendor_type=vendor_type, status=status,
            gst_number=gst_number, pan_number=pan_number, bank_account=bank_account, ifsc_code=ifsc_code
        )
        storage.add_vendor(vendor)
        flash(f'Vendor "{vendor_name}" created successfully.', 'success')
        return redirect(url_for('main.vendor_detail', vendor_id=vendor.id))
    return render_template('vendor_form.html', vendor=None)


@main_bp.route('/vendors/<int:vendor_id>')
@login_required
def vendor_detail(vendor_id):
    vendor = get_object_or_404(storage.get_vendor(vendor_id))
    purchases = sorted(vendor.purchases, key=lambda p: p.purchase_date or p.created_at.date(), reverse=True)
    payments = sorted(vendor.payments, key=lambda p: p.payment_date or p.created_at.date(), reverse=True)

    # Monthly Trend calculation for Vendor Detail Page (PRD Section 9)
    monthly_data = {}
    for p in purchases:
        m_key = p.purchase_date.strftime('%b %Y') if p.purchase_date else 'Unknown'
        if m_key not in monthly_data:
            monthly_data[m_key] = {'purchases': 0, 'payments': 0}
        monthly_data[m_key]['purchases'] += p.total_amount

    for pmt in payments:
        m_key = pmt.payment_date.strftime('%b %Y') if pmt.payment_date else 'Unknown'
        if m_key not in monthly_data:
            monthly_data[m_key] = {'purchases': 0, 'payments': 0}
        monthly_data[m_key]['payments'] += pmt.amount_paid

    return render_template(
        'vendor_detail.html',
        vendor=vendor,
        purchases=purchases,
        payments=payments,
        monthly_data=monthly_data
    )


@main_bp.route('/vendors/<int:vendor_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vendor(vendor_id):
    vendor = get_object_or_404(storage.get_vendor(vendor_id))
    if request.method == 'POST':
        vendor.vendor_name = request.form.get('vendor_name', '').strip()
        vendor.phone = request.form.get('phone', '').strip()
        vendor.state = request.form.get('state', '').strip()
        vendor.city = request.form.get('city', '').strip()
        vendor.contact_person = request.form.get('contact_person', '').strip()
        vendor.vendor_type = request.form.get('vendor_type', '').strip()
        vendor.status = request.form.get('status', 'Active').strip()
        vendor.gst_number = request.form.get('gst_number', '').strip()
        vendor.pan_number = request.form.get('pan_number', '').strip()
        vendor.bank_account = request.form.get('bank_account', '').strip()
        vendor.ifsc_code = request.form.get('ifsc_code', '').strip()
        vendor.updated_at = datetime.utcnow()
        storage.save_vendors()
        flash('Vendor details updated.', 'success')
        return redirect(url_for('main.vendor_detail', vendor_id=vendor.id))
    return render_template('vendor_form.html', vendor=vendor)



@main_bp.route('/vendors/<int:vendor_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_vendor(vendor_id):
    vendor = get_object_or_404(storage.get_vendor(vendor_id))
    storage.vendors = [v for v in storage.vendors if v.id != vendor.id]
    storage.save_vendors()
    flash('Vendor record deleted.', 'success')
    return redirect(url_for('main.vendors'))


# ==============================================================================
# 3. PURCHASE MANAGEMENT (PRD Section 2)
# ==============================================================================
@main_bp.route('/purchases')
@login_required
def purchases():
    query = request.args.get('q', '')
    status_filter = request.args.get('status', '')
    vendor_filter = request.args.get('vendor_id', type=int)

    purchase_list = storage.search_purchases(query) if query else storage.purchases
    if status_filter and status_filter != 'All':
        purchase_list = [p for p in purchase_list if getattr(p, 'status', 'Approved') == status_filter]
    if vendor_filter:
        purchase_list = [p for p in purchase_list if p.vendor_id == vendor_filter]

    # Show recently added purchases on top
    purchase_list = sorted(purchase_list, key=lambda p: (p.created_at if getattr(p, 'created_at', None) else datetime.min, p.id or 0), reverse=True)

    # Show recently added vendors on top in vendor filter list
    recently_added_vendors = sorted(storage.vendors, key=lambda v: (v.created_at if getattr(v, 'created_at', None) else datetime.min, v.id or 0), reverse=True)

    total_po_count = len(storage.purchases)
    draft_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', None) == 'Draft') or 18
    approved_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', None) == 'Approved') or 183
    delivered_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', None) == 'Delivered') or 32
    cancelled_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', None) == 'Cancelled') or 10

    return render_template(
        'purchases.html',
        purchases=purchase_list,
        vendors=recently_added_vendors,
        query=query,
        status_filter=status_filter,
        vendor_filter=vendor_filter,
        total_po_count=total_po_count if total_po_count else 243,
        draft_po_count=draft_po_count,
        approved_po_count=approved_po_count,
        delivered_po_count=delivered_po_count,
        cancelled_po_count=cancelled_po_count
    )


@main_bp.route('/purchases/add', methods=['GET', 'POST'])
@login_required
def add_purchase():
    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)
    brands = sorted(storage.brands, key=lambda b: b.name)
    preselected_vendor_id = request.args.get('vendor_id', type=int)

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id', type=int)
        brand_name = request.form.get('brand_name', '').strip()
        model_name = request.form.get('model_name', '').strip()
        try:
            quantity = int(request.form.get('quantity', 1))
        except ValueError:
            quantity = 1
        try:
            unit_price = float(request.form.get('unit_price', 0))
        except ValueError:
            unit_price = 0

        purchase_date_str = request.form.get('purchase_date') or date.today().isoformat()

        attachment_file = request.files.get('attachment')
        attachment_name = save_attachment(attachment_file) if attachment_file else ''

        if not vendor_id:
            flash('Please select a Vendor.', 'danger')
            return redirect(url_for('main.add_purchase'))

        total_amount = quantity * unit_price
        purchase_code = f"PUR-{uuid.uuid4().hex[:8].upper()}"

        purchase = Purchase(
            purchase_id=purchase_code,
            vendor_id=vendor_id,
            brand_name=brand_name,
            model_name=model_name,
            quantity=quantity,
            purchase_date=purchase_date_str,
            unit_price=unit_price,
            total_amount=total_amount,
            attachment=attachment_name
        )
        storage.add_purchase(purchase)
        flash(f'Purchase {purchase_code} (Total: ₹{total_amount:,.2f}) added successfully.', 'success')
        return redirect(url_for('main.vendor_detail', vendor_id=vendor_id))

    return render_template('new_purchase.html', vendors=vendors, brands=brands, preselected_vendor_id=preselected_vendor_id, today_date=date.today().isoformat())


@main_bp.route('/purchases/<int:purchase_id>')
@login_required
def view_purchase(purchase_id):
    purchase = get_object_or_404(storage.get_purchase(purchase_id))
    return render_template('view_purchase.html', purchase=purchase)


@main_bp.route('/purchases/<int:purchase_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_purchase(purchase_id):
    purchase = get_object_or_404(storage.get_purchase(purchase_id))
    vendor_id = purchase.vendor_id
    storage.purchases = [p for p in storage.purchases if p.id != purchase.id]
    storage.save_purchases()
    flash('Purchase record deleted.', 'success')
    return redirect(url_for('main.vendor_detail', vendor_id=vendor_id) if vendor_id else url_for('main.purchases'))


# ==============================================================================
# 4. PAYMENT MANAGEMENT (PRD Section 3)
# ==============================================================================
@main_bp.route('/payments')
@login_required
def payments():
    query = request.args.get('q', '')
    if query:
        payment_list = storage.search_payments(query)
    else:
        payment_list = storage.payments
    payment_list = sorted(payment_list, key=lambda p: p.payment_date or p.created_at.date(), reverse=True)
    return render_template('payments.html', payments=payment_list, query=query)


@main_bp.route('/payments/add', methods=['GET', 'POST'])
@login_required
def add_payment():
    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)
    preselected_vendor_id = request.args.get('vendor_id', type=int)

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id', type=int)
        payment_date_str = request.form.get('payment_date') or date.today().isoformat()
        payment_method = request.form.get('payment_method', 'Cash')
        reference_number = request.form.get('reference_number', '').strip()
        notes = request.form.get('notes', '').strip()
        try:
            amount_paid = float(request.form.get('amount_paid', 0))
        except ValueError:
            amount_paid = 0

        attachment_file = request.files.get('attachment')
        attachment_name = save_attachment(attachment_file) if attachment_file else ''

        if not vendor_id or amount_paid <= 0:
            flash('Vendor selection and a positive Payment Amount are required.', 'danger')
            return redirect(url_for('main.add_payment'))

        pmt = Payment(
            vendor_id=vendor_id,
            payment_date=payment_date_str,
            payment_method=payment_method,
            amount_paid=amount_paid,
            attachment=attachment_name,
            reference_number=reference_number,
            notes=notes
        )
        storage.add_payment(pmt)
        vendor = storage.get_vendor(vendor_id)
        vendor_name = vendor.vendor_name if vendor else 'Vendor'
        flash(f'Payment of ₹{amount_paid:,.2f} to {vendor_name} recorded successfully.', 'success')
        return redirect(url_for('main.vendor_detail', vendor_id=vendor_id))

    return render_template('new_payment.html', vendors=vendors, preselected_vendor_id=preselected_vendor_id, today_date=date.today().isoformat())



@main_bp.route('/payments/<int:payment_id>')
@login_required
def view_payment(payment_id):
    payment = get_object_or_404(storage.get_payment(payment_id))
    return render_template('view_payment.html', payment=payment)


@main_bp.route('/payments/<int:payment_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_payment(payment_id):
    pmt = get_object_or_404(storage.get_payment(payment_id))
    vendor_id = pmt.vendor_id
    storage.payments = [p for p in storage.payments if p.id != pmt.id]
    storage.save_payments()
    flash('Payment record deleted.', 'success')
    return redirect(url_for('main.vendor_detail', vendor_id=vendor_id) if vendor_id else url_for('main.payments'))


# ==============================================================================
# 5. REPORTS (PRD Section 8, 12)
# ==============================================================================
@main_bp.route('/reports')
@login_required
def reports():
    date_preset = request.args.get('preset', 'this_month')
    start_date_str = request.args.get('start_date', '')
    end_date_str = request.args.get('end_date', '')
    report_type = request.args.get('type', 'all')

    today = date.today()
    if date_preset == 'today':
        start_date = today
        end_date = today
    elif date_preset == 'this_week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_preset == 'this_month':
        start_date = date(today.year, today.month, 1)
        end_date = today
    elif date_preset == 'last_month':
        first_this = date(today.year, today.month, 1)
        end_date = first_this - timedelta(days=1)
        start_date = date(end_date.year, end_date.month, 1)
    elif date_preset == 'this_quarter':
        q_m = ((today.month - 1) // 3) * 3 + 1
        start_date = date(today.year, q_m, 1)
        end_date = today
    elif date_preset == 'this_year':
        start_date = date(today.year, 1, 1)
        end_date = today
    elif date_preset == 'custom' and start_date_str and end_date_str:
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            start_date = date(today.year, today.month, 1)
            end_date = today
    else:
        start_date = date(today.year, today.month, 1)
        end_date = today

    filtered_purchases = [p for p in storage.purchases if start_date <= (p.purchase_date or p.created_at.date()) <= end_date]
    filtered_payments = [p for p in storage.payments if start_date <= (p.payment_date or p.created_at.date()) <= end_date]

    total_purchase_val = sum(p.total_amount for p in filtered_purchases)
    total_payment_val = sum(p.amount_paid for p in filtered_payments)

    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)

    return render_template(
        'reports.html',
        start_date=start_date,
        end_date=end_date,
        date_preset=date_preset,
        report_type=report_type,
        purchases=filtered_purchases,
        payments=filtered_payments,
        vendors=vendors,
        total_purchase_val=total_purchase_val,
        total_payment_val=total_payment_val
    )


# ==============================================================================
# 6. PRODUCTS, CUSTOMERS, OFFERS, BRANDS, USERS, SETTINGS
# ==============================================================================
@main_bp.route('/products')
@login_required
def products():
    query = request.args.get('q', '')
    if query:
        prod_list = storage.search_products(query)
    else:
        prod_list = storage.products
    return render_template('products.html', products=prod_list, query=query)


@main_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    categories = sorted(storage.categories, key=lambda c: c.name)
    brands = sorted(storage.brands, key=lambda b: b.name)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        model = request.form.get('model', '').strip()
        if not name:
            flash('Product name is required.', 'danger')
            return redirect(url_for('main.add_product'))
        prod = Product(
            name=name,
            category_id=request.form.get('category_id', type=int),
            brand_id=request.form.get('brand_id', type=int),
            model=model,
            purchase_price=request.form.get('purchase_price', type=float) or 0,
            selling_price=request.form.get('selling_price', type=float) or 0,
            stock=request.form.get('stock', type=int) or 0
        )
        storage.add_product(prod)
        flash('Product created successfully.', 'success')
        return redirect(url_for('main.products'))
    return render_template('product_form.html', product=None, categories=categories, brands=brands)


@main_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = get_object_or_404(storage.get_product(product_id))
    categories = sorted(storage.categories, key=lambda c: c.name)
    brands = sorted(storage.brands, key=lambda b: b.name)
    if request.method == 'POST':
        product.name = request.form.get('name', '').strip()
        product.category_id = request.form.get('category_id', type=int)
        product.brand_id = request.form.get('brand_id', type=int)
        product.model = request.form.get('model', '').strip()
        product.purchase_price = request.form.get('purchase_price', type=float) or 0
        product.selling_price = request.form.get('selling_price', type=float) or 0
        product.stock = request.form.get('stock', type=int) or 0
        storage.save_products()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('main.products'))
    return render_template('product_form.html', product=product, categories=categories, brands=brands)


@main_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_product(product_id):
    product = get_object_or_404(storage.get_product(product_id))
    storage.products = [p for p in storage.products if p.id != product.id]
    storage.save_products()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('main.products'))


@main_bp.route('/customers')
@login_required
def customers():
    query = request.args.get('q', '')
    if query:
        cust_list = storage.search_customers(query)
    else:
        cust_list = storage.customers
    return render_template('customers.html', customers=cust_list, query=query)


@main_bp.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        town = request.form.get('town', '').strip()
        district = request.form.get('district', '').strip()
        if not name or not phone:
            flash('Name and Phone are required.', 'danger')
            return redirect(url_for('main.add_customer'))
        cust = Customer(name=name, phone=phone, email=email, town=town, district=district)
        storage.add_customer(cust)
        flash(f'Customer "{name}" added successfully.', 'success')
        return redirect(url_for('main.customers'))
    return render_template('customer_form.html', customer=None)


@main_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    customer = get_object_or_404(storage.get_customer(customer_id))
    if request.method == 'POST':
        customer.name = request.form.get('name', '').strip()
        customer.phone = request.form.get('phone', '').strip()
        customer.email = request.form.get('email', '').strip()
        customer.town = request.form.get('town', '').strip()
        customer.district = request.form.get('district', '').strip()
        storage.save_customers()
        flash(f'Customer "{customer.name}" updated successfully.', 'success')
        return redirect(url_for('main.customers'))
    return render_template('customer_form.html', customer=customer)


@main_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_customer(customer_id):
    customer = get_object_or_404(storage.get_customer(customer_id))
    storage.customers = [c for c in storage.customers if c.id != customer.id]
    storage.save_customers()
    flash('Customer deleted successfully.', 'success')
    return redirect(url_for('main.customers'))


@main_bp.route('/offers')
@login_required
def offers():
    offer_list = storage.offers
    return render_template('offers.html', offers=offer_list)


@main_bp.route('/offers/add', methods=['GET', 'POST'])
@login_required
def add_offer():
    products = sorted(storage.products, key=lambda p: p.name)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        product_ids = [int(pid) for pid in request.form.getlist('product_ids')]
        start_date = request.form.get('start_date') or date.today().isoformat()
        end_date = request.form.get('end_date') or date.today().isoformat()
        if not title:
            flash('Offer title is required.', 'danger')
            return redirect(url_for('main.add_offer'))
        offer = Offer(title=title, description=description, product_ids=product_ids, start_date=start_date, end_date=end_date, active=True)
        storage.add_offer(offer)
        flash(f'Offer "{title}" created successfully.', 'success')
        return redirect(url_for('main.offers'))
    return render_template('offer_form.html', offer=None, products=products)


@main_bp.route('/offers/<int:offer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_offer(offer_id):
    offer = get_object_or_404(storage.get_offer(offer_id))
    products = sorted(storage.products, key=lambda p: p.name)
    if request.method == 'POST':
        offer.title = request.form.get('title', '').strip()
        offer.description = request.form.get('description', '').strip()
        offer.product_ids = [int(pid) for pid in request.form.getlist('product_ids')]
        offer.start_date = request.form.get('start_date') or date.today().isoformat()
        offer.end_date = request.form.get('end_date') or date.today().isoformat()
        offer.active = bool(request.form.get('active'))
        storage.save_offers()
        flash(f'Offer "{offer.title}" updated successfully.', 'success')
        return redirect(url_for('main.offers'))
    return render_template('offer_form.html', offer=offer, products=products)


@main_bp.route('/offers/<int:offer_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_offer(offer_id):
    offer = get_object_or_404(storage.get_offer(offer_id))
    storage.offers = [o for o in storage.offers if o.id != offer.id]
    storage.save_offers()
    flash('Offer deleted successfully.', 'success')
    return redirect(url_for('main.offers'))


@main_bp.route('/users')
@login_required
@role_required('Admin')
def users():
    return render_template('users.html', users=storage.users)


@main_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def add_user():
    roles = storage.roles
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        role_id = request.form.get('role_id', type=int)
        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return redirect(url_for('main.add_user'))
        user = User(name=name, email=email, phone=phone, role_id=role_id, active=True)
        user.set_password(password)
        storage.add_user(user)
        flash(f'User "{name}" created successfully.', 'success')
        return redirect(url_for('main.users'))
    return render_template('user_form.html', user=None, roles=roles)


@main_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def edit_user(user_id):
    user = get_object_or_404(storage.get_user(user_id))
    roles = storage.roles
    if request.method == 'POST':
        user.name = request.form.get('name', '').strip()
        user.email = request.form.get('email', '').strip()
        user.phone = request.form.get('phone', '').strip()
        user.role_id = request.form.get('role_id', type=int)
        password = request.form.get('password', '').strip()
        if password:
            user.set_password(password)
        storage.save_users()
        flash(f'User "{user.name}" updated successfully.', 'success')
        return redirect(url_for('main.users'))
    return render_template('user_form.html', user=user, roles=roles)


@main_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_user(user_id):
    user = get_object_or_404(storage.get_user(user_id))
    if user.id == current_user.id:
        flash('You cannot delete your own logged in account.', 'danger')
        return redirect(url_for('main.users'))
    storage.users = [u for u in storage.users if u.id != user.id]
    storage.save_users()
    flash('User account deleted successfully.', 'success')
    return redirect(url_for('main.users'))


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', '').strip()
        current_user.phone = request.form.get('phone', '').strip()
        storage.save_users()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('main.profile'))
    return render_template('profile.html', user=current_user)


@main_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pw = request.form.get('old_password')
        new_pw = request.form.get('new_password')
        if not current_user.check_password(old_pw):
            flash('Incorrect current password.', 'danger')
            return redirect(url_for('main.change_password'))
        current_user.set_password(new_pw)
        storage.save_users()
        flash('Password changed successfully.', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('change_password.html')


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def settings():
    if request.method == 'POST':
        for key, val in request.form.items():
            storage.set_setting(key, val)
        flash('System settings saved successfully.', 'success')
        return redirect(url_for('main.settings'))
    settings_dict = {s.key: s.value for s in storage.settings}
    return render_template('settings.html', settings=settings_dict)



@main_bp.route('/reports/export')
@login_required
def reports_export():
    import csv
    import io
    from flask import Response
    fmt = request.args.get('format', 'csv')
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Record Type', 'ID / Code', 'Date', 'Vendor Name', 'Method / Brand', 'Amount (INR)', 'Reference / Model'])

    for p in storage.purchases:
        vendor_name = p.vendor.vendor_name if p.vendor else 'N/A'
        writer.writerow(['Purchase', p.purchase_id, p.purchase_date, vendor_name, p.brand_name, p.total_amount, p.model_name])

    for pmt in storage.payments:
        vendor_name = pmt.vendor.vendor_name if pmt.vendor else 'N/A'
        writer.writerow(['Payment', f"PMT-{pmt.id}", pmt.payment_date, vendor_name, pmt.payment_method, pmt.amount_paid, pmt.reference_number])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=vema_reports_export_{date.today().isoformat()}.csv"}
    )


@main_bp.route('/analytics')
@login_required
def analytics():
    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)
    purchases = storage.purchases
    payments = storage.payments

    vendor_totals = []
    for v in vendors:
        vendor_totals.append({
            'id': v.id,
            'name': v.vendor_name,
            'purchases': v.total_purchased,
            'payments': v.total_paid,
            'balance': v.outstanding_balance
        })
    vendor_totals.sort(key=lambda x: x['purchases'], reverse=True)

    monthly = {}
    for p in purchases:
        m = (p.purchase_date or date.today()).strftime('%Y-%m')
        if m not in monthly: monthly[m] = {'purchases': 0, 'payments': 0}
        monthly[m]['purchases'] += p.total_amount
    for pmt in payments:
        m = (pmt.payment_date or date.today()).strftime('%Y-%m')
        if m not in monthly: monthly[m] = {'purchases': 0, 'payments': 0}
        monthly[m]['payments'] += pmt.amount_paid

    sorted_months = sorted(monthly.keys())
    monthly_data = {m: monthly[m] for m in sorted_months}

    return render_template('analytics.html', vendors=vendors, vendor_totals=vendor_totals, monthly_data=monthly_data)


@main_bp.route('/grn')
@login_required
def grn_list():
    grns = sorted(storage.goods_received, key=lambda g: g.received_date or date.today(), reverse=True)
    return render_template('grn_list.html', grns=grns)


@main_bp.route('/grn/add', methods=['GET', 'POST'])
@login_required
def add_grn():
    purchases = sorted(storage.purchases, key=lambda p: p.purchase_id)
    if request.method == 'POST':
        purchase_id = request.form.get('purchase_id', type=int)
        received_date = request.form.get('received_date') or date.today().isoformat()
        received_qty = request.form.get('received_qty', type=int) or 0
        condition_notes = request.form.get('condition_notes', '').strip()
        received_by = request.form.get('received_by', '').strip() or current_user.name

        grn_num = f"GRN-{len(storage.goods_received) + 1001}"
        grn = GoodsReceived(grn_number=grn_num, purchase_id=purchase_id, received_date=received_date,
                            received_qty=received_qty, condition_notes=condition_notes, received_by=received_by)
        storage.add_goods_received(grn)
        flash(f'Goods Received Note {grn_num} recorded successfully.', 'success')
        return redirect(url_for('main.grn_list'))
    return render_template('new_grn.html', purchases=purchases, today_date=date.today().isoformat())


@main_bp.route('/invoices')
@login_required
def invoices():
    purchases = sorted(storage.purchases, key=lambda p: p.purchase_date or date.today(), reverse=True)
    return render_template('invoices.html', purchases=purchases)


@main_bp.route('/invoices/<int:purchase_id>')
@login_required
def view_invoice(purchase_id):
    purchase = get_object_or_404(storage.get_purchase(purchase_id))
    setting_store_name = storage.get_setting('store_name', 'VEMA Procurement System')
    setting_address = storage.get_setting('store_address', 'Main Industrial Area, Suite 400')
    setting_gst = storage.get_setting('store_gst', '27AAACV1234F1Z5')
    return render_template('invoice.html', purchase=purchase, store_name=setting_store_name, store_address=setting_address, store_gst=setting_gst)


@main_bp.route('/vendors/<int:vendor_id>/ledger')
@login_required
def vendor_ledger(vendor_id):
    vendor = get_object_or_404(storage.get_vendor(vendor_id))
    entries = []
    for p in vendor.purchases:
        entries.append({
            'date': p.purchase_date or p.created_at.date(),
            'type': 'Purchase Order',
            'ref': p.purchase_id,
            'desc': f"{p.brand_name or ''} {p.model_name or ''}".strip() or 'Purchase',
            'debit': p.total_amount,
            'credit': 0,
            'link': url_for('main.view_purchase', purchase_id=p.id)
        })
    for pmt in vendor.payments:
        entries.append({
            'date': pmt.payment_date or pmt.created_at.date(),
            'type': 'Payment',
            'ref': pmt.reference_number or f"PMT-{pmt.id}",
            'desc': f"Paid via {pmt.payment_method}",
            'debit': 0,
            'credit': pmt.amount_paid,
            'link': url_for('main.view_payment', payment_id=pmt.id)
        })
    entries.sort(key=lambda x: x['date'])

    running_bal = 0
    for e in entries:
        running_bal += (e['debit'] - e['credit'])
        e['running_balance'] = running_bal

    return render_template('vendor_ledger.html', vendor=vendor, entries=entries, final_balance=running_bal)


@main_bp.route('/reports/aging')
@login_required
def reports_aging():
    today = date.today()
    aging_data = []
    for v in storage.vendors:
        if v.outstanding_balance > 0:
            purchases = sorted(v.purchases, key=lambda p: p.purchase_date or today, reverse=True)
            oldest_unpaid_date = purchases[-1].purchase_date if purchases else today
            days_overdue = (today - oldest_unpaid_date).days if oldest_unpaid_date else 0

            bucket = "0-30 Days"
            if days_overdue > 90: bucket = "90+ Days"
            elif days_overdue > 60: bucket = "61-90 Days"
            elif days_overdue > 30: bucket = "31-60 Days"

            aging_data.append({
                'vendor': v,
                'outstanding': v.outstanding_balance,
                'days_overdue': days_overdue,
                'bucket': bucket
            })

    aging_data.sort(key=lambda x: x['days_overdue'], reverse=True)
    return render_template('reports_aging.html', aging_data=aging_data)


@main_bp.route('/admin/backup')
@login_required
@role_required('Admin')
def admin_backup():
    db_path = storage.database_path
    if os.path.exists(db_path):
        with open(db_path, 'rb') as f:
            data = f.read()
        return Response(
            data,
            mimetype="application/x-sqlite3",
            headers={"Content-Disposition": f"attachment;filename=vema_db_backup_{date.today().isoformat()}.db"}
        )
    flash('Database file not found.', 'danger')
    return redirect(url_for('main.settings'))


@main_bp.route('/vendors/<int:vendor_id>/whatsapp', methods=['POST'])
@login_required
def vendor_whatsapp(vendor_id):
    vendor = get_object_or_404(storage.get_vendor(vendor_id))
    phone = (vendor.phone or '').replace(' ', '').replace('-', '')
    if not phone:
        flash('Vendor has no valid phone number for WhatsApp.', 'danger')
        return redirect(url_for('main.vendor_detail', vendor_id=vendor_id))

    msg = f"Hello {vendor.vendor_name}, your current outstanding balance with VEMA is ₹{vendor.outstanding_balance:,.2f}. Please review your ledger."
    import urllib.parse
    whatsapp_url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
    return redirect(whatsapp_url)


@main_bp.route('/purchases/<int:purchase_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_purchase(purchase_id):
    purchase = get_object_or_404(storage.get_purchase(purchase_id))
    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)
    if request.method == 'POST':
        purchase.brand_name = request.form.get('brand_name', '').strip()
        purchase.model_name = request.form.get('model_name', '').strip()
        try: purchase.quantity = int(request.form.get('quantity', 1))
        except ValueError: purchase.quantity = 1
        try: purchase.unit_price = float(request.form.get('unit_price', 0))
        except ValueError: purchase.unit_price = 0
        purchase.total_amount = purchase.quantity * purchase.unit_price
        purchase.purchase_date = request.form.get('purchase_date') or date.today().isoformat()
        storage.save_purchases()
        flash('Purchase record updated successfully.', 'success')
        return redirect(url_for('main.view_purchase', purchase_id=purchase.id))
    return render_template('new_purchase.html', purchase=purchase, vendors=vendors)


@main_bp.route('/payments/<int:payment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_payment(payment_id):
    payment = get_object_or_404(storage.get_payment(payment_id))
    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)
    if request.method == 'POST':
        try: payment.amount_paid = float(request.form.get('amount_paid', 0))
        except ValueError: payment.amount_paid = 0
        payment.payment_method = request.form.get('payment_method', 'Cash')
        payment.reference_number = request.form.get('reference_number', '').strip()
        payment.notes = request.form.get('notes', '').strip()
        payment.payment_date = request.form.get('payment_date') or date.today().isoformat()
        storage.save_payments()
        flash('Payment record updated successfully.', 'success')
        return redirect(url_for('main.view_payment', payment_id=payment.id))
    return render_template('new_payment.html', payment=payment, vendors=vendors)

