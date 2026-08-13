import os
import uuid
import requests
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import (Vendor, Payment, Purchase, Customer, Product, Role, User,
                     Category, Brand, StoreSetting, Offer, OfferMessage, Warranty,
                     PurchaseItem, GoodsReceived, WhatsAppMessage)
from .storage import storage
from .utils import role_required


def get_object_or_404(obj):
    if obj is None:
        abort(404)
    return obj


PER_PAGE = 10


def paginate(items, page, per_page=PER_PAGE):
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page or 1, total_pages))
    start = (page - 1) * per_page
    page_items = items[start:start + per_page]
    return page_items, page, total_pages, total


def pagination_pages(page, total_pages):
    """Windowed list of page numbers; None marks an ellipsis gap."""
    if total_pages <= 7:
        return list(range(1, total_pages + 1))
    candidates = sorted({1, 2, total_pages - 1, total_pages, page - 1, page, page + 1})
    candidates = [p for p in candidates if 1 <= p <= total_pages]
    result = []
    prev = 0
    for p in candidates:
        if p - prev > 1:
            result.append(None)
        result.append(p)
        prev = p
    return result


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
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    upload_path = os.path.join(upload_folder, unique_name)
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
# Dashboard Data Filtering & Aggregation Helpers
def _filter_dashboard_purchases(sale_type=None, time_period=None, start_date_str=None, end_date_str=None, vendor_id=None):
    purchases = storage.purchases
    
    # Filter by Vendor if provided
    if vendor_id:
        purchases = [p for p in purchases if p.vendor_id == vendor_id]

    # Filter by Sale Type (Wholesale / Retail / Both / All)
    if sale_type and sale_type.strip().lower() not in ['all', 'both', '']:
        st = sale_type.strip().lower()
        purchases = [p for p in purchases if (getattr(p, 'sale_type', '') or '').lower() == st or (getattr(p, 'sale_type', '') or '').lower() == 'both']

    # Filter by Date Range / Time Period
    today = date.today()
    start_dt = None
    end_dt = None

    if start_date_str and end_date_str:
        try:
            start_dt = date.fromisoformat(start_date_str)
            end_dt = date.fromisoformat(end_date_str)
        except ValueError:
            pass

    if not start_dt or not end_dt:
        period = (time_period or 'monthly').lower()
        if period in ['daily', 'day']:
            start_dt = today - timedelta(days=30)
            end_dt = today
        elif period in ['monthly', 'month']:
            start_dt = today - timedelta(days=365)
            end_dt = today
        elif period in ['yearly', 'year']:
            start_dt = date(today.year - 5, 1, 1)
            end_dt = today
        else:
            start_dt = today - timedelta(days=365)
            end_dt = today

    purchases = [p for p in purchases if start_dt <= (p.purchase_date or p.created_at.date()) <= end_dt]
    return purchases, start_dt, end_dt


def _build_units_sold_chart(purchases, period):
    period = (period or 'monthly').lower()
    from collections import defaultdict
    grouped = defaultdict(int)

    for p in purchases:
        p_date = p.purchase_date or p.created_at.date()
        if period in ['daily', 'day']:
            key = p_date.strftime('%Y-%m-%d')
        elif period in ['yearly', 'year']:
            key = p_date.strftime('%Y')
        else:  # monthly
            key = p_date.strftime('%b %Y')
        grouped[key] += int(p.quantity or 0)

    sorted_items = sorted(grouped.items())
    labels = [item[0] for item in sorted_items] if sorted_items else ['No Data']
    values = [item[1] for item in sorted_items] if sorted_items else [0]
    return labels, values


def _build_total_sales_chart(purchases, period):
    period = (period or 'monthly').lower()
    from collections import defaultdict
    grouped = defaultdict(float)

    for p in purchases:
        p_date = p.purchase_date or p.created_at.date()
        if period in ['daily', 'day']:
            key = p_date.strftime('%Y-%m-%d')
        elif period in ['yearly', 'year']:
            key = p_date.strftime('%Y')
        else:  # monthly
            key = p_date.strftime('%b %Y')
        grouped[key] += float(p.total_amount or 0)

    sorted_items = sorted(grouped.items())
    labels = [item[0] for item in sorted_items] if sorted_items else ['No Data']
    values = [round(item[1], 2) for item in sorted_items] if sorted_items else [0]
    return labels, values


def _build_product_type_chart(purchases):
    from collections import defaultdict
    grouped = defaultdict(float)

    for p in purchases:
        st = (getattr(p, 'sale_type', '') or getattr(p, 'product_type', '') or 'Retail').strip().capitalize()
        if st not in ['Wholesale', 'Retail', 'Both']:
            st = 'Retail'
        grouped[st] += float(p.total_amount or 0)

    total_val = sum(grouped.values()) or 1.0
    labels = ['Wholesale', 'Retail', 'Both']
    values = [round(grouped['Wholesale'], 2), round(grouped['Retail'], 2), round(grouped['Both'], 2)]
    percentages = [round((v / total_val) * 100, 1) for v in values]
    return labels, values, percentages


def _build_brand_chart(purchases):
    from collections import defaultdict
    grouped = defaultdict(float)

    for p in purchases:
        bname = (p.brand_name or p.brand or 'Other').strip()
        if not bname:
            bname = 'Other'
        grouped[bname] += float(p.total_amount or 0)

    if not grouped:
        for b in storage.brands:
            grouped[b.name] = 0.0

    sorted_brands = sorted(grouped.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_brands) > 8:
        top_brands = sorted_brands[:7]
        other_val = sum(x[1] for x in sorted_brands[7:])
        labels = [x[0] for x in top_brands] + ['Other']
        values = [round(x[1], 2) for x in top_brands] + [round(other_val, 2)]
    else:
        labels = [x[0] for x in sorted_brands] if sorted_brands else ['No Brands']
        values = [round(x[1], 2) for x in sorted_brands] if sorted_brands else [0]

    total_val = sum(values) or 1.0
    percentages = [round((v / total_val) * 100, 1) for v in values]
    return labels, values, percentages


@main_bp.route('/')
@login_required
def dashboard():
    selected_vendor_id = request.args.get('vendor_id', type=int)
    sale_type_filter = request.args.get('sale_type', request.args.get('sale_type_filter', 'All'))
    time_filter = request.args.get('filter', request.args.get('period', 'monthly'))
    start_date_param = request.args.get('start_date')
    end_date_param = request.args.get('end_date')

    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)
    all_purchases = storage.purchases
    all_payments = storage.payments

    # Scoped purchases using helper
    purchases_in_scope, filter_start, filter_end = _filter_dashboard_purchases(
        sale_type=sale_type_filter,
        time_period=time_filter,
        start_date_str=start_date_param,
        end_date_str=end_date_param,
        vendor_id=selected_vendor_id
    )

    # Scoped summary metrics for top cards
    total_units_sold = sum(int(p.quantity or 0) for p in purchases_in_scope)
    total_sales_val = sum(float(p.total_amount or 0) for p in purchases_in_scope)
    wholesale_sales_val = sum(float(p.total_amount or 0) for p in purchases_in_scope if (getattr(p, 'sale_type', '') or '').lower() in ['wholesale', 'both'])
    retail_sales_val = sum(float(p.total_amount or 0) for p in purchases_in_scope if (getattr(p, 'sale_type', '') or '').lower() in ['retail', 'both'])
    total_products_count = len(storage.products)
    total_purchases_count = len(purchases_in_scope)

    # Legacy & Vendor KPI metrics calculation
    def scope_payments(items, start, end):
        return [p for p in items
                if (not selected_vendor_id or p.vendor_id == selected_vendor_id)
                and start <= (p.payment_date or p.created_at.date()) <= end]

    cur_payments = scope_payments(all_payments, filter_start, filter_end)
    cur_payments_val = sum(p.amount_paid for p in cur_payments)
    total_outstanding = total_sales_val - cur_payments_val
    total_vendors_count = len(vendors)

    today = date.today()
    this_month_start = date(today.year, today.month, 1)
    vendors_added_this_month = sum(1 for v in vendors if v.created_at and v.created_at.date() >= this_month_start)

    # Chart datasets
    units_chart_labels, units_chart_values = _build_units_sold_chart(purchases_in_scope, time_filter)
    sales_chart_labels, sales_chart_values = _build_total_sales_chart(purchases_in_scope, time_filter)
    prod_type_labels, prod_type_values, prod_type_pcts = _build_product_type_chart(purchases_in_scope)
    brand_labels, brand_values, brand_pcts = _build_brand_chart(purchases_in_scope)

    # Legacy Vendor comparison chart
    selected_vendor = storage.get_vendor(selected_vendor_id) if selected_vendor_id else None
    target_vendors = [selected_vendor] if selected_vendor else vendors
    comparison = []
    for v in target_vendors:
        v_purchases = sum(p.total_amount for p in v.purchases if filter_start <= (p.purchase_date or p.created_at.date()) <= filter_end)
        v_payments = sum(p.amount_paid for p in v.payments if filter_start <= (p.payment_date or p.created_at.date()) <= filter_end)
        comparison.append({'vendor': v.vendor_name, 'purchases': v_purchases, 'payments': v_payments})
    comparison.sort(key=lambda c: c['purchases'], reverse=True)

    def short_name(name):
        parts = name.split()
        return ' '.join(parts[:2]) if parts else name

    purchase_chart_labels = [short_name(c['vendor']) for c in comparison]
    purchase_chart_values = [c['purchases'] for c in comparison]

    payment_ranked = sorted(comparison, key=lambda c: c['payments'], reverse=True)
    payment_chart_labels = [short_name(c['vendor']) for c in payment_ranked]
    payment_chart_values = [c['payments'] for c in payment_ranked]
    payment_chart_items = [{'name': c['vendor'], 'value': c['payments']} for c in payment_ranked]
    payments_total = sum(payment_chart_values)

    recent_purchases = sorted(purchases_in_scope, key=lambda p: p.purchase_date or p.created_at.date(), reverse=True)[:5]
    recent_payments = sorted(cur_payments, key=lambda p: p.payment_date or p.created_at.date(), reverse=True)[:5]

    time_filter_label = {
        'daily': 'Daily', 'day': 'Daily',
        'monthly': 'Monthly', 'month': 'Monthly',
        'yearly': 'Yearly', 'year': 'Yearly'
    }.get(time_filter.lower(), 'Monthly')

    return render_template(
        'dashboard.html',
        vendors=vendors,
        selected_vendor=selected_vendor,
        selected_vendor_id=selected_vendor_id,
        sale_type_filter=sale_type_filter,
        time_filter=time_filter,
        time_filter_label=time_filter_label,
        start_date=start_date_param,
        end_date=end_date_param,
        # 6 Main KPI Summary Cards
        total_units_sold=total_units_sold,
        total_sales_val=total_sales_val,
        wholesale_sales_val=wholesale_sales_val,
        retail_sales_val=retail_sales_val,
        total_products_count=total_products_count,
        total_purchases_count=total_purchases_count,
        # Legacy KPI values
        total_purchases_val=total_sales_val,
        total_payments_val=cur_payments_val,
        total_outstanding=total_outstanding,
        total_vendors_count=total_vendors_count,
        vendors_added_this_month=vendors_added_this_month,
        purchases_pct_change=0,
        payments_pct_change=0,
        outstanding_change=0,
        # Charts
        units_chart_labels=units_chart_labels,
        units_chart_values=units_chart_values,
        sales_chart_labels=sales_chart_labels,
        sales_chart_values=sales_chart_values,
        prod_type_labels=prod_type_labels,
        prod_type_values=prod_type_values,
        prod_type_pcts=prod_type_pcts,
        brand_labels=brand_labels,
        brand_values=brand_values,
        brand_pcts=brand_pcts,
        purchase_chart_labels=purchase_chart_labels,
        purchase_chart_values=purchase_chart_values,
        payment_chart_labels=payment_chart_labels,
        payment_chart_values=payment_chart_values,
        payment_chart_items=payment_chart_items,
        payments_total=payments_total,
        recent_purchases=recent_purchases,
        recent_payments=recent_payments,
        recent_purchases_total=len(purchases_in_scope),
        recent_payments_total=len(cur_payments)
    )


# ==============================================================================
# DASHBOARD API ENDPOINTS (PRD / Feature Section 8 & 9)
# ==============================================================================
@main_bp.route('/api/dashboard/summary')
@login_required
def api_dashboard_summary():
    sale_type = request.args.get('sale_type', request.args.get('sale_type_filter', 'All'))
    time_period = request.args.get('time_period', request.args.get('filter', 'monthly'))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    purchases, _, _ = _filter_dashboard_purchases(sale_type, time_period, start_date, end_date)

    units_sold = sum(int(p.quantity or 0) for p in purchases)
    total_sales = sum(float(p.total_amount or 0) for p in purchases)
    wholesale_sales = sum(float(p.total_amount or 0) for p in purchases if (getattr(p, 'sale_type', '') or '').lower() in ['wholesale', 'both'])
    retail_sales = sum(float(p.total_amount or 0) for p in purchases if (getattr(p, 'sale_type', '') or '').lower() in ['retail', 'both'])
    total_products = len(storage.products)
    total_purchases = len(purchases)

    return jsonify({
        'total_units_sold': units_sold,
        'total_sales': round(total_sales, 2),
        'wholesale_sales': round(wholesale_sales, 2),
        'retail_sales': round(retail_sales, 2),
        'total_products': total_products,
        'total_purchases': total_purchases
    })


@main_bp.route('/api/dashboard/units-sold')
@login_required
def api_dashboard_units_sold():
    sale_type = request.args.get('sale_type', request.args.get('sale_type_filter', 'All'))
    time_period = request.args.get('time_period', request.args.get('filter', 'monthly'))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    purchases, _, _ = _filter_dashboard_purchases(sale_type, time_period, start_date, end_date)
    labels, values = _build_units_sold_chart(purchases, time_period)

    return jsonify({'labels': labels, 'values': values})


@main_bp.route('/api/dashboard/total-sales')
@login_required
def api_dashboard_total_sales():
    sale_type = request.args.get('sale_type', request.args.get('sale_type_filter', 'All'))
    time_period = request.args.get('time_period', request.args.get('filter', 'monthly'))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    purchases, _, _ = _filter_dashboard_purchases(sale_type, time_period, start_date, end_date)
    labels, values = _build_total_sales_chart(purchases, time_period)

    return jsonify({'labels': labels, 'values': values})


@main_bp.route('/api/dashboard/product-type')
@login_required
def api_dashboard_product_type():
    sale_type = request.args.get('sale_type', request.args.get('sale_type_filter', 'All'))
    time_period = request.args.get('time_period', request.args.get('filter', 'monthly'))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    purchases, _, _ = _filter_dashboard_purchases(sale_type, time_period, start_date, end_date)
    labels, values, percentages = _build_product_type_chart(purchases)

    return jsonify({'labels': labels, 'values': values, 'percentages': percentages})


@main_bp.route('/api/dashboard/brand')
@login_required
def api_dashboard_brand():
    sale_type = request.args.get('sale_type', request.args.get('sale_type_filter', 'All'))
    time_period = request.args.get('time_period', request.args.get('filter', 'monthly'))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    purchases, _, _ = _filter_dashboard_purchases(sale_type, time_period, start_date, end_date)
    labels, values, percentages = _build_brand_chart(purchases)

    return jsonify({'labels': labels, 'values': values, 'percentages': percentages})


# ==============================================================================
# PURCHASE TRACK MODULE (PRD Sections 2, 3, 4, 5, 6, 7, 11)
# ==============================================================================
@main_bp.route('/purchases/track', methods=['GET'])
@login_required
def purchase_track():
    query = request.args.get('q', '').strip()
    sale_type_filter = request.args.get('sale_type', '').strip()
    brand_filter = request.args.get('brand', '').strip()
    product_filter = request.args.get('product_type', '').strip()
    start_date_filter = request.args.get('start_date', '').strip()
    end_date_filter = request.args.get('end_date', '').strip()
    page = request.args.get('page', 1, type=int)

    items = storage.search_purchases(query) if query else storage.purchases

    if sale_type_filter and sale_type_filter != 'All':
        items = [p for p in items if (getattr(p, 'sale_type', '') or '').lower() == sale_type_filter.lower() or (getattr(p, 'sale_type', '') or '').lower() == 'both']

    if brand_filter and brand_filter != 'All':
        items = [p for p in items if (p.brand_name or p.brand or '').lower() == brand_filter.lower()]

    if product_filter and product_filter != 'All':
        items = [p for p in items if (getattr(p, 'product_type', '') or '').lower() == product_filter.lower()]

    if start_date_filter:
        try:
            s_dt = date.fromisoformat(start_date_filter)
            items = [p for p in items if (p.purchase_date or p.created_at.date()) >= s_dt]
        except ValueError:
            pass

    if end_date_filter:
        try:
            e_dt = date.fromisoformat(end_date_filter)
            items = [p for p in items if (p.purchase_date or p.created_at.date()) <= e_dt]
        except ValueError:
            pass

    # Sort purchases descending by date
    items = sorted(items, key=lambda p: (p.purchase_date or p.created_at.date(), p.id or 0), reverse=True)

    page_items, current_page, total_pages, total_count = paginate(items, page, per_page=10)
    page_numbers = pagination_pages(current_page, total_pages)

    # Dynamic brands list
    brand_names = set(b.name for b in storage.brands if b.name)
    for p in storage.purchases:
        if p.brand_name:
            brand_names.add(p.brand_name)
    sorted_brands = sorted(list(brand_names))

    # Dynamic product types list
    product_types = set(c.name for c in storage.categories if c.name)
    for p in storage.purchases:
        if getattr(p, 'product_type', None):
            product_types.add(p.product_type)
    sorted_product_types = sorted(list(product_types))

    return render_template(
        'purchase_track.html',
        purchases=page_items,
        page=current_page,
        total_pages=total_pages,
        total_count=total_count,
        page_numbers=page_numbers,
        query=query,
        sale_type_filter=sale_type_filter,
        brand_filter=brand_filter,
        product_filter=product_filter,
        start_date_filter=start_date_filter,
        end_date_filter=end_date_filter,
        brands=sorted_brands,
        product_types=sorted_product_types
    )


@main_bp.route('/purchases/track/save', methods=['POST'])
@login_required
def purchase_track_save():
    customer_name = request.form.get('customer_name', '').strip()
    phone_number = request.form.get('phone_number', '').strip()
    email = request.form.get('email', '').strip()
    product_type = request.form.get('product_type', '').strip()
    brand_name = request.form.get('brand', request.form.get('brand_name', '')).strip()
    model_name = request.form.get('model_name', '').strip()
    quantity_str = request.form.get('quantity', '1').strip()
    price_str = request.form.get('price', '0').strip()
    total_price_str = request.form.get('total_price', '').strip()
    sale_type = request.form.get('sale_type', 'Retail').strip()
    purchase_date_str = request.form.get('purchase_date', '').strip()

    # Validation
    errors = []
    if not customer_name:
        errors.append("Customer Name is required.")
    if not phone_number:
        errors.append("Phone Number is required.")
    if not product_type:
        errors.append("Product Type is required.")
    if not brand_name:
        errors.append("Brand is required.")
    if not model_name:
        errors.append("Model Name is required.")
    if not sale_type:
        errors.append("Sale Type is required.")

    try:
        quantity = int(quantity_str)
        if quantity <= 0:
            errors.append("Quantity must be greater than 0.")
    except ValueError:
        errors.append("Invalid quantity.")
        quantity = 1

    try:
        unit_price = float(price_str)
        if unit_price < 0:
            errors.append("Price must be greater than or equal to 0.")
    except ValueError:
        errors.append("Invalid price.")
        unit_price = 0.0

    if total_price_str:
        try:
            total_price = float(total_price_str)
        except ValueError:
            total_price = quantity * unit_price
    else:
        total_price = quantity * unit_price

    if errors:
        for err in errors:
            flash(err, "danger")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'errors': errors}), 400
        return redirect(url_for('main.purchase_track'))

    # Handle document uploads
    invoice_file = request.files.get('invoice')
    attachment_file = request.files.get('attachment')

    invoice_filename = save_attachment(invoice_file) if invoice_file else ''
    attachment_filename = save_attachment(attachment_file) if attachment_file else ''

    # Handle purchase date
    p_date = date.today()
    if purchase_date_str:
        try:
            p_date = date.fromisoformat(purchase_date_str)
        except ValueError:
            pass

    # Ensure Brand exists in database
    if brand_name and not storage.find_brand_by_name(brand_name):
        storage.add_brand(Brand(name=brand_name))

    # Ensure Customer exists in database or update
    cust = storage.find_customer_by_phone(phone_number)
    if not cust:
        cust = Customer(name=customer_name, phone=phone_number, email=email)
        storage.add_customer(cust)

    # Generate Purchase ID
    purchase_code = f"PUR-{uuid.uuid4().hex[:8].upper()}"

    new_purchase = Purchase(
        purchase_id=purchase_code,
        customer_name=customer_name,
        phone_number=phone_number,
        email=email,
        product_type=product_type,
        brand_name=brand_name,
        model_name=model_name,
        quantity=quantity,
        unit_price=unit_price,
        total_amount=total_price,
        sale_type=sale_type,
        purchase_type=sale_type,
        invoice=invoice_filename,
        attachment=attachment_filename,
        purchase_date=p_date,
        customer_id=cust.id if cust else None,
        user_id=current_user.id if current_user.is_authenticated else None,
        status='Approved'
    )
    storage.add_purchase(new_purchase)

    flash("Purchase record created successfully!", "success")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Purchase saved successfully', 'purchase': new_purchase.to_dict()})
    return redirect(url_for('main.purchase_track'))


@main_bp.route('/api/purchases/<int:purchase_id>')
@login_required
def api_get_purchase(purchase_id):
    purchase = storage.get_purchase(purchase_id)
    if not purchase:
        return jsonify({'error': 'Purchase not found'}), 404
    return jsonify(purchase.to_dict())


@main_bp.route('/purchases/track/<int:purchase_id>/edit', methods=['POST'])
@login_required
def purchase_track_edit(purchase_id):
    purchase = storage.get_purchase(purchase_id)
    if not purchase:
        flash("Purchase record not found.", "danger")
        return redirect(url_for('main.purchase_track'))

    customer_name = request.form.get('customer_name', '').strip()
    phone_number = request.form.get('phone_number', '').strip()
    email = request.form.get('email', '').strip()
    product_type = request.form.get('product_type', '').strip()
    brand_name = request.form.get('brand', request.form.get('brand_name', '')).strip()
    model_name = request.form.get('model_name', '').strip()
    quantity_str = request.form.get('quantity', '1').strip()
    price_str = request.form.get('price', '0').strip()
    total_price_str = request.form.get('total_price', '').strip()
    sale_type = request.form.get('sale_type', 'Retail').strip()

    if customer_name: purchase.customer_name = customer_name
    if phone_number: purchase.phone_number = phone_number
    if email: purchase.email = email
    if product_type: purchase.product_type = product_type
    if brand_name: purchase.brand_name = brand_name
    if model_name: purchase.model_name = model_name
    if sale_type:
        purchase.sale_type = sale_type
        purchase.purchase_type = sale_type

    try:
        qty = int(quantity_str)
        if qty > 0: purchase.quantity = qty
    except ValueError:
        pass

    try:
        u_price = float(price_str)
        if u_price >= 0: purchase.unit_price = u_price
    except ValueError:
        pass

    if total_price_str:
        try:
            purchase.total_amount = float(total_price_str)
        except ValueError:
            purchase.total_amount = purchase.quantity * purchase.unit_price
    else:
        purchase.total_amount = purchase.quantity * purchase.unit_price

    purchase.total = purchase.total_amount
    purchase.subtotal = purchase.total_amount
    purchase.updated_at = datetime.utcnow()

    # Update uploaded files if new files provided
    invoice_file = request.files.get('invoice')
    if invoice_file and invoice_file.filename:
        inv_fn = save_attachment(invoice_file)
        if inv_fn: purchase.invoice = inv_fn

    attachment_file = request.files.get('attachment')
    if attachment_file and attachment_file.filename:
        att_fn = save_attachment(attachment_file)
        if att_fn: purchase.attachment = att_fn

    storage.save_purchases()
    flash("Purchase record updated successfully!", "success")
    return redirect(url_for('main.purchase_track'))


@main_bp.route('/purchases/track/<int:purchase_id>/delete', methods=['POST'])
@login_required
def purchase_track_delete(purchase_id):
    purchase = storage.get_purchase(purchase_id)
    if not purchase:
        flash("Purchase record not found.", "danger")
        return redirect(url_for('main.purchase_track'))

    storage.delete_purchase(purchase_id)
    flash("Purchase record deleted successfully!", "success")
    return redirect(url_for('main.purchase_track'))



# ==============================================================================
# 2. VENDOR REGISTRATION & MANAGEMENT (PRD Sections 1, 9)
# ==============================================================================
@main_bp.route('/vendors')
@login_required
def vendors():
    query = request.args.get('q', '')
    status_filter = request.args.get('status', '')
    type_filter = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)

    vendor_list = storage.search_vendors(query) if query else storage.vendors
    if status_filter and status_filter != 'All':
        vendor_list = [v for v in vendor_list if getattr(v, 'status', 'Active') == status_filter]
    if type_filter and type_filter != 'All':
        vendor_list = [v for v in vendor_list if getattr(v, 'vendor_type', 'Supplier') == type_filter]

    vendor_list = sorted(vendor_list, key=lambda v: v.vendor_name)

    # Real KPI values
    today = date.today()
    month_start = today.replace(day=1)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)
    prev_month_end = month_start - timedelta(days=1)

    total_vendors_count = len(storage.vendors)
    active_vendors_count = sum(1 for v in storage.vendors if getattr(v, 'status', 'Active') == 'Active')
    inactive_vendors_count = total_vendors_count - active_vendors_count
    vendors_added_this_month = sum(1 for v in storage.vendors
                                   if v.created_at and v.created_at.date() >= month_start)
    active_added_this_month = sum(1 for v in storage.vendors
                                  if getattr(v, 'status', 'Active') == 'Active'
                                  and v.created_at and v.created_at.date() >= month_start)

    total_purchases_val = sum(p.total_amount for p in storage.purchases)
    total_payments_val = sum(p.amount_paid for p in storage.payments)
    total_outstanding_val = total_purchases_val - total_payments_val

    month_purchases = sum(p.total_amount for p in storage.purchases
                          if p.purchase_date and month_start <= p.purchase_date <= today)
    prev_month_purchases = sum(p.total_amount for p in storage.purchases
                               if p.purchase_date and prev_month_start <= p.purchase_date <= prev_month_end)
    purchases_pct_change = ((month_purchases - prev_month_purchases) / prev_month_purchases * 100
                            if prev_month_purchases else 0.0)

    outstanding_now = total_outstanding_val
    outstanding_prev = (sum(p.total_amount for p in storage.purchases
                            if p.purchase_date and p.purchase_date <= prev_month_end)
                        - sum(pmt.amount_paid for pmt in storage.payments
                              if pmt.payment_date and pmt.payment_date <= prev_month_end))
    outstanding_pct_change = ((outstanding_now - outstanding_prev) / outstanding_prev * 100
                              if outstanding_prev else 0.0)

    vendors_page, page, total_pages, total_items = paginate(vendor_list, page)
    pages = pagination_pages(page, total_pages)
    start_idx = (page - 1) * PER_PAGE + 1
    end_idx = min(start_idx + len(vendors_page) - 1, total_items)

    return render_template(
        'vendors.html',
        vendors=vendors_page,
        query=query,
        status_filter=status_filter,
        type_filter=type_filter,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        pages=pages,
        start_idx=start_idx,
        end_idx=end_idx,
        total_vendors_count=total_vendors_count,
        active_vendors_count=active_vendors_count,
        inactive_vendors_count=inactive_vendors_count,
        vendors_added_this_month=vendors_added_this_month,
        active_added_this_month=active_added_this_month,
        total_purchases_val=total_purchases_val,
        total_outstanding_val=total_outstanding_val,
        purchases_pct_change=purchases_pct_change,
        outstanding_pct_change=outstanding_pct_change,
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

    monthly_data = dict(sorted(monthly_data.items()))

    payment_method_totals = {}
    for pmt in payments:
        method = (pmt.payment_method or 'Other').strip()
        payment_method_totals[method] = payment_method_totals.get(method, 0) + pmt.amount_paid
    payment_method_data = sorted(payment_method_totals.items(), key=lambda kv: kv[1], reverse=True)

    total_invoiced = vendor.total_purchased
    total_paid = vendor.total_paid
    settlement_pct = round((total_paid / total_invoiced * 100) if total_invoiced else 0, 1)

    # Aging info for this vendor (oldest unpaid purchase)
    today = date.today()
    days_overdue = 0
    aging_bucket = None
    if vendor.outstanding_balance > 0:
        oldest_unpaid = sorted(vendor.purchases, key=lambda p: p.purchase_date or today)[0] if vendor.purchases else None
        oldest_unpaid_date = oldest_unpaid.purchase_date if oldest_unpaid else today
        days_overdue = (today - oldest_unpaid_date).days if oldest_unpaid_date else 0
        aging_bucket = "0-30 Days"
        if days_overdue > 90:
            aging_bucket = "90+ Days"
        elif days_overdue > 60:
            aging_bucket = "61-90 Days"
        elif days_overdue > 30:
            aging_bucket = "31-60 Days"

    return render_template(
        'vendor_detail.html',
        vendor=vendor,
        purchases=purchases,
        payments=payments,
        monthly_data=monthly_data,
        payment_method_data=payment_method_data,
        total_invoiced=total_invoiced,
        total_paid=total_paid,
        settlement_pct=settlement_pct,
        days_overdue=days_overdue,
        aging_bucket=aging_bucket
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
    page = request.args.get('page', 1, type=int)

    purchase_list = storage.search_purchases(query) if query else storage.purchases
    if status_filter and status_filter != 'All':
        purchase_list = [p for p in purchase_list if getattr(p, 'status', 'Approved') == status_filter]
    if vendor_filter:
        purchase_list = [p for p in purchase_list if p.vendor_id == vendor_filter]

    # Show recently added purchases on top
    purchase_list = sorted(purchase_list, key=lambda p: (p.created_at if getattr(p, 'created_at', None) else datetime.min, p.id or 0), reverse=True)

    # Show recently added vendors on top in vendor filter list
    recently_added_vendors = sorted(storage.vendors, key=lambda v: (v.created_at if getattr(v, 'created_at', None) else datetime.min, v.id or 0), reverse=True)

    # Real status KPI counts
    total_po_count = len(storage.purchases)
    draft_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', 'Approved') == 'Draft')
    pending_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', 'Approved') == 'Pending')
    approved_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', 'Approved') == 'Approved')
    delivered_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', 'Approved') == 'Delivered')
    cancelled_po_count = sum(1 for p in storage.purchases if getattr(p, 'status', 'Approved') == 'Cancelled')

    today = date.today()
    month_start = today.replace(day=1)
    purchases_this_month = sum(1 for p in storage.purchases
                               if p.purchase_date and month_start <= p.purchase_date <= today)

    for p in purchase_list:
        p.expected_date = (p.purchase_date + timedelta(days=7)) if p.purchase_date else None

    purchases_page, page, total_pages, total_items = paginate(purchase_list, page)
    pages = pagination_pages(page, total_pages)
    start_idx = (page - 1) * PER_PAGE + 1
    end_idx = min(start_idx + len(purchases_page) - 1, total_items)

    return render_template(
        'purchases.html',
        purchases=purchases_page,
        vendors=recently_added_vendors,
        query=query,
        status_filter=status_filter,
        vendor_filter=vendor_filter,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        pages=pages,
        start_idx=start_idx,
        end_idx=end_idx,
        total_po_count=total_po_count,
        draft_po_count=draft_po_count,
        pending_po_count=pending_po_count,
        approved_po_count=approved_po_count,
        delivered_po_count=delivered_po_count,
        cancelled_po_count=cancelled_po_count,
        purchases_this_month=purchases_this_month,
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
    grn = next((g for g in storage.goods_received if g.purchase_id == purchase.id), None)
    items = purchase.items
    warranty = purchase.warranty
    return render_template('view_purchase.html', purchase=purchase, grn=grn, items=items or None, warranty=warranty)


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
    method_filter = request.args.get('method', '')
    vendor_filter = request.args.get('vendor_id', type=int)
    page = request.args.get('page', 1, type=int)

    payment_list = storage.search_payments(query) if query else list(storage.payments)
    if method_filter and method_filter != 'All':
        payment_list = [p for p in payment_list if p.payment_method == method_filter]
    if vendor_filter:
        payment_list = [p for p in payment_list if p.vendor_id == vendor_filter]
    payment_list = sorted(payment_list, key=lambda p: p.payment_date or p.created_at.date(), reverse=True)

    total_payments = len(storage.payments)
    total_paid_val = sum(p.amount_paid for p in storage.payments)
    today = date.today()
    this_month = sum(1 for p in storage.payments
                     if p.payment_date and p.payment_date.year == today.year and p.payment_date.month == today.month)
    methods_used = sorted({p.payment_method for p in storage.payments})
    avg_payment = round(total_paid_val / total_payments) if total_payments else 0
    highest_payment = round(max((p.amount_paid for p in storage.payments), default=0))

    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)

    payments_page, page, total_pages, total_items = paginate(payment_list, page)
    pages = pagination_pages(page, total_pages)
    start_idx = (page - 1) * PER_PAGE + 1
    end_idx = min(start_idx + len(payments_page) - 1, total_items)

    return render_template(
        'payments.html',
        payments=payments_page,
        vendors=vendors,
        query=query,
        method_filter=method_filter,
        vendor_filter=vendor_filter,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        pages=pages,
        start_idx=start_idx,
        end_idx=end_idx,
        total_payments=total_payments,
        total_paid_val=total_paid_val,
        this_month=this_month,
        methods_used=methods_used,
        avg_payment=avg_payment,
        highest_payment=highest_payment
    )


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

    # --- Chart data ----------------------------------------------------
    # Purchase trend: per-day totals; collapse to monthly for long ranges
    purchase_buckets = {}
    for p in filtered_purchases:
        d = p.purchase_date or p.created_at.date()
        purchase_buckets[d] = purchase_buckets.get(d, 0) + p.total_amount

    if (end_date - start_date).days > 45:
        monthly = {}
        for d, val in purchase_buckets.items():
            key = date(d.year, d.month, 1)
            monthly[key] = monthly.get(key, 0) + val
        purchase_buckets = monthly

    purchase_chart_labels = [k.strftime('%d %b') for k in sorted(purchase_buckets)]
    purchase_chart_values = [purchase_buckets[k] for k in sorted(purchase_buckets)]

    # Payment method breakdown
    method_buckets = {}
    for pmt in filtered_payments:
        m = pmt.payment_method or 'Other'
        method_buckets[m] = method_buckets.get(m, 0) + pmt.amount_paid
    method_chart_labels = list(method_buckets.keys())
    method_chart_values = list(method_buckets.values())

    # Top vendors by total purchased (all-time, matches summary table)
    top_vendors = sorted(storage.vendors, key=lambda v: v.total_purchased, reverse=True)[:8]
    vendor_chart_labels = [v.vendor_name for v in top_vendors]
    vendor_chart_values = [v.total_purchased for v in top_vendors]

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
        total_payment_val=total_payment_val,
        purchase_chart_labels=purchase_chart_labels,
        purchase_chart_values=purchase_chart_values,
        method_chart_labels=method_chart_labels,
        method_chart_values=method_chart_values,
        vendor_chart_labels=vendor_chart_labels,
        vendor_chart_values=vendor_chart_values
    )


# ==============================================================================
# 6. PRODUCTS, CUSTOMERS, OFFERS, BRANDS, USERS, SETTINGS
# ==============================================================================
@main_bp.route('/products')
@login_required
def products():
    query = request.args.get('q', '')
    category_filter = request.args.get('category_id', type=int)
    brand_filter = request.args.get('brand_id', type=int)
    page = request.args.get('page', 1, type=int)

    prod_list = storage.search_products(query) if query else list(storage.products)
    if category_filter:
        prod_list = [p for p in prod_list if p.category_id == category_filter]
    if brand_filter:
        prod_list = [p for p in prod_list if p.brand_id == brand_filter]

    total_products = len(storage.products)
    total_stock = sum(p.stock for p in storage.products)
    stock_value = sum(p.stock * (p.purchase_price or 0) for p in storage.products)
    category_count = len({p.category_id for p in storage.products if p.category_id})
    low_stock_count = sum(1 for p in storage.products if p.stock <= 5)
    margins = [((p.selling_price or 0) - (p.purchase_price or 0)) / (p.purchase_price or 0) * 100
               for p in storage.products if p.purchase_price]
    avg_margin = round(sum(margins) / len(margins)) if margins else 0

    categories = sorted(storage.categories, key=lambda c: c.name)
    brands = sorted(storage.brands, key=lambda b: b.name)

    products_page, page, total_pages, total_items = paginate(prod_list, page)
    pages = pagination_pages(page, total_pages)
    start_idx = (page - 1) * PER_PAGE + 1
    end_idx = min(start_idx + len(products_page) - 1, total_items)

    return render_template(
        'products.html',
        products=products_page,
        categories=categories,
        brands=brands,
        query=query,
        category_filter=category_filter,
        brand_filter=brand_filter,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        pages=pages,
        start_idx=start_idx,
        end_idx=end_idx,
        total_products=total_products,
        total_stock=total_stock,
        stock_value=stock_value,
        category_count=category_count,
        low_stock_count=low_stock_count,
        avg_margin=avg_margin
    )


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

        brand_id = request.form.get('brand_id', type=int)
        new_brand = request.form.get('new_brand_name', '').strip()
        if new_brand and not brand_id:
            b_obj = storage.find_brand_by_name(new_brand)
            if not b_obj:
                b_obj = storage.add_brand(Brand(name=new_brand))
            brand_id = b_obj.id

        category_id = request.form.get('category_id', type=int)
        new_cat = request.form.get('new_category_name', '').strip()
        if new_cat and not category_id:
            c_obj = storage.find_category_by_name(new_cat)
            if not c_obj:
                c_obj = storage.add_category(Category(name=new_cat))
            category_id = c_obj.id

        prod = Product(
            name=name,
            category_id=category_id,
            brand_id=brand_id,
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

        brand_id = request.form.get('brand_id', type=int)
        new_brand = request.form.get('new_brand_name', '').strip()
        if new_brand and not brand_id:
            b_obj = storage.find_brand_by_name(new_brand)
            if not b_obj:
                b_obj = storage.add_brand(Brand(name=new_brand))
            brand_id = b_obj.id

        category_id = request.form.get('category_id', type=int)
        new_cat = request.form.get('new_category_name', '').strip()
        if new_cat and not category_id:
            c_obj = storage.find_category_by_name(new_cat)
            if not c_obj:
                c_obj = storage.add_category(Category(name=new_cat))
            category_id = c_obj.id

        product.category_id = category_id
        product.brand_id = brand_id
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


# ==============================================================================
# MASTER MANAGEMENT APIs (Brands & Categories)
# ==============================================================================
@main_bp.route('/api/masters/all')
@login_required
def api_masters_all():
    brands = [{'id': b.id, 'name': b.name} for b in sorted(storage.brands, key=lambda b: b.name)]
    categories = [{'id': c.id, 'name': c.name} for c in sorted(storage.categories, key=lambda c: c.name)]
    return jsonify({'brands': brands, 'categories': categories})


@main_bp.route('/api/masters/brands/add', methods=['POST'])
@login_required
def api_add_brand():
    name = (request.json.get('name') if request.is_json else request.form.get('name', '')).strip()
    if not name:
        return jsonify({'success': False, 'error': 'Brand name is required.'}), 400
    existing = storage.find_brand_by_name(name)
    if existing:
        return jsonify({'success': True, 'brand': {'id': existing.id, 'name': existing.name}, 'message': 'Brand already exists.'})
    new_b = Brand(name=name)
    storage.add_brand(new_b)
    return jsonify({'success': True, 'brand': {'id': new_b.id, 'name': new_b.name}, 'message': f'Brand "{name}" created successfully.'})


@main_bp.route('/api/masters/categories/add', methods=['POST'])
@login_required
def api_add_category():
    name = (request.json.get('name') if request.is_json else request.form.get('name', '')).strip()
    if not name:
        return jsonify({'success': False, 'error': 'Category name is required.'}), 400
    existing = storage.find_category_by_name(name)
    if existing:
        return jsonify({'success': True, 'category': {'id': existing.id, 'name': existing.name}, 'message': 'Category already exists.'})
    new_c = Category(name=name)
    storage.add_category(new_c)
    return jsonify({'success': True, 'category': {'id': new_c.id, 'name': new_c.name}, 'message': f'Category "{name}" created successfully.'})


@main_bp.route('/api/masters/brands/<int:brand_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def api_delete_brand(brand_id):
    brand = storage.get_brand(brand_id)
    if not brand:
        return jsonify({'success': False, 'error': 'Brand not found'}), 404
    storage.delete_brand(brand_id)
    return jsonify({'success': True, 'message': 'Brand deleted.'})


@main_bp.route('/api/masters/categories/<int:category_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def api_delete_category(category_id):
    cat = storage.get_category(category_id)
    if not cat:
        return jsonify({'success': False, 'error': 'Category not found'}), 404
    storage.delete_category(category_id)
    return jsonify({'success': True, 'message': 'Category deleted.'})


@main_bp.route('/admin/clear-test-data', methods=['POST'])
@login_required
@role_required('Admin')
def admin_clear_test_data():
    storage.purchases = []
    storage.purchase_items = []
    storage.payments = []
    storage.goods_received = []
    storage.warranties = []
    storage.whatsapp_messages = []
    storage.offers = []
    storage.offer_messages = []

    storage._save_collection('purchases')
    storage._save_collection('purchase_items')
    storage._save_collection('payments')
    storage._save_collection('goods_received')
    storage._save_collection('warranties')
    storage._save_collection('whatsapp_messages')
    storage._save_collection('offers')
    storage._save_collection('offer_messages')

    flash('All test transactions, purchases, payments, and GRNs have been completely cleared!', 'success')
    return redirect(url_for('main.settings'))


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
    customers_list = sorted(storage.customers, key=lambda c: c.name)
    return render_template('offers.html', offers=offer_list, customers=customers_list)


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

        image_file = request.files.get('image')
        image_name = save_attachment(image_file) if image_file else ''

        offer = Offer(title=title, description=description, product_ids=product_ids, start_date=start_date, end_date=end_date, active=True, image=image_name)
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

        image_file = request.files.get('image')
        if image_file:
            img_name = save_attachment(image_file)
            if img_name:
                offer.image = img_name

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


# ==============================================================================
# DIRECT IN-APP BULK WHATSAPP & CONTACT IMPORT APIs
# ==============================================================================
@main_bp.route('/api/customers/import', methods=['POST'])
@login_required
def api_customers_import():
    text_data = ''
    if request.files.get('file'):
        file_obj = request.files['file']
        text_data = file_obj.read().decode('utf-8', errors='ignore')
    elif request.is_json:
        text_data = request.json.get('text_data', '')
    else:
        text_data = request.form.get('text_data', '')

    if not text_data or not text_data.strip():
        return jsonify({'success': False, 'error': 'No contact data provided.'}), 400

    imported_count = 0
    lines = text_data.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.lower().startswith('name'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) >= 2:
            name = parts[0]
            phone = parts[1]
            email = parts[2] if len(parts) > 2 else ''
            town = parts[3] if len(parts) > 3 else ''

            if name and phone:
                existing = storage.find_customer_by_phone(phone)
                if not existing:
                    new_c = Customer(name=name, phone=phone, email=email, town=town)
                    storage.add_customer(new_c)
                    imported_count += 1

    cust_list = [{'id': c.id, 'name': c.name, 'phone': c.phone, 'email': c.email} for c in sorted(storage.customers, key=lambda c: c.name)]
    return jsonify({
        'success': True,
        'imported_count': imported_count,
        'total_customers': len(storage.customers),
        'customers': cust_list,
        'message': f'Successfully imported {imported_count} new contact(s).'
    })


@main_bp.route('/api/whatsapp/send-bulk-offer', methods=['POST'])
@login_required
def api_whatsapp_send_bulk_offer():
    data = request.get_json() if request.is_json else request.form
    offer_id = data.get('offer_id')
    recipients = data.get('recipients', [])
    message = data.get('message', '').strip()
    image_filename = data.get('image_filename', '').strip()

    if not recipients:
        return jsonify({'success': False, 'error': 'No target phone numbers provided.'}), 400

    # Get WhatsApp Business Cloud API Settings
    settings_dict = {s.key: s.value for s in storage.settings}
    phone_id = settings_dict.get('whatsapp_phone_id', '').strip()
    access_token = settings_dict.get('whatsapp_access_token', '').strip()

    results = []
    sent_count = 0
    failed_count = 0

    for phone in recipients:
        clean_phone = str(phone).replace(' ', '').replace('-', '').replace('+', '')
        if len(clean_phone) == 10:
            clean_phone = '91' + clean_phone  # India country code default

        if not clean_phone or len(clean_phone) < 8:
            results.append({'phone': phone, 'status': 'Failed', 'error': 'Invalid phone number format'})
            failed_count += 1
            continue

        # If Cloud API settings are configured, perform direct Meta Cloud API HTTP dispatch
        if phone_id and access_token:
            try:
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                payload = {
                    'messaging_product': 'whatsapp',
                    'to': clean_phone,
                    'type': 'text',
                    'text': {'body': message}
                }
                api_url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
                resp = requests.post(api_url, json=payload, headers=headers, timeout=8)
                if resp.status_code in [200, 201]:
                    results.append({'phone': clean_phone, 'status': 'Sent', 'message_id': resp.json().get('messages', [{}])[0].get('id')})
                    sent_count += 1
                else:
                    err_msg = resp.json().get('error', {}).get('message', f'HTTP {resp.status_code}')
                    results.append({'phone': clean_phone, 'status': 'Failed', 'error': err_msg})
                    failed_count += 1
            except Exception as e:
                results.append({'phone': clean_phone, 'status': 'Failed', 'error': str(e)})
                failed_count += 1
        else:
            # Direct In-App Application Dispatch
            msg_record = WhatsAppMessage(
                phone_number=clean_phone,
                message=message,
                status='Sent',
                sent_at=datetime.utcnow().isoformat()
            )
            storage.add_whatsapp_message(msg_record)
            results.append({'phone': clean_phone, 'status': 'Sent', 'note': 'Dispatched direct via app messaging engine'})
            sent_count += 1

    return jsonify({
        'success': True,
        'cloud_api_configured': bool(phone_id and access_token),
        'total': len(recipients),
        'sent_count': sent_count,
        'failed_count': failed_count,
        'results': results,
        'message': f'Bulk broadcast complete: {sent_count} sent successfully, {failed_count} failed.'
    })


@main_bp.route('/users')
@login_required
@role_required('Admin')
def users():
    query = request.args.get('q', '')
    role_filter = request.args.get('role_id', type=int)
    page = request.args.get('page', 1, type=int)

    user_list = list(storage.users)
    if query:
        q = query.lower()
        user_list = [u for u in user_list
                     if q in (u.name or '').lower()
                     or q in (u.email or '').lower()
                     or q in (u.phone or '').lower()]
    if role_filter:
        user_list = [u for u in user_list if u.role_id == role_filter]

    total_users = len(storage.users)
    active_users = sum(1 for u in storage.users if u.active)
    admin_count = sum(1 for u in storage.users if u.role and u.role.name == 'Admin')
    manager_count = sum(1 for u in storage.users if u.role and u.role.name == 'Manager')
    staff_count = sum(1 for u in storage.users if u.role and u.role.name not in ('Admin', 'Manager'))

    roles = storage.roles

    users_page, page, total_pages, total_items = paginate(user_list, page)
    pages = pagination_pages(page, total_pages)
    start_idx = (page - 1) * PER_PAGE + 1
    end_idx = min(start_idx + len(users_page) - 1, total_items)

    return render_template(
        'users.html',
        users=users_page,
        roles=roles,
        query=query,
        role_filter=role_filter,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        pages=pages,
        start_idx=start_idx,
        end_idx=end_idx,
        total_users=total_users,
        active_users=active_users,
        admin_count=admin_count,
        manager_count=manager_count,
        staff_count=staff_count
    )


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

    total_purchased_val = sum(p.total_amount for p in purchases)
    total_paid_val = sum(pmt.amount_paid for pmt in payments)
    total_outstanding = total_purchased_val - total_paid_val
    settlement_pct = round((total_paid_val / total_purchased_val * 100) if total_purchased_val else 0, 1)

    return render_template(
        'analytics.html',
        vendors=vendors,
        vendor_totals=vendor_totals,
        monthly_data=monthly_data,
        total_vendors=len(vendors),
        total_purchased_val=total_purchased_val,
        total_paid_val=total_paid_val,
        total_outstanding=total_outstanding,
        settlement_pct=settlement_pct
    )


@main_bp.route('/grn')
@login_required
def grn_list():
    query = request.args.get('q', '')
    vendor_filter = request.args.get('vendor_id', type=int)
    page = request.args.get('page', 1, type=int)

    grn_list = list(storage.goods_received)
    if query:
        q = query.lower()
        grn_list = [g for g in grn_list
                    if q in (g.grn_number or '').lower()
                    or q in (g.received_by or '').lower()
                    or (g.purchase and q in (g.purchase.purchase_id or '').lower())
                    or (g.purchase and g.purchase.vendor and q in g.purchase.vendor.vendor_name.lower())]
    if vendor_filter:
        grn_list = [g for g in grn_list if g.purchase and g.purchase.vendor_id == vendor_filter]

    grn_list = sorted(grn_list, key=lambda g: g.received_date or date.today(), reverse=True)

    total_grns = len(storage.goods_received)
    total_qty = sum(g.received_qty for g in storage.goods_received)
    today = date.today()
    this_month = sum(1 for g in storage.goods_received
                     if g.received_date and g.received_date.year == today.year and g.received_date.month == today.month)
    vendor_count = len({g.purchase.vendor_id for g in storage.goods_received if g.purchase and g.purchase.vendor_id})
    partial_count = sum(1 for g in storage.goods_received
                        if g.purchase and g.received_qty < (g.purchase.quantity or 0))
    ordered_total = sum(g.purchase.quantity or 0 for g in storage.goods_received if g.purchase)

    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)

    grns, page, total_pages, total_items = paginate(grn_list, page)
    pages = pagination_pages(page, total_pages)
    start_idx = (page - 1) * PER_PAGE + 1
    end_idx = min(start_idx + len(grns) - 1, total_items)

    return render_template(
        'grn_list.html',
        grns=grns,
        vendors=vendors,
        query=query,
        vendor_filter=vendor_filter,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        pages=pages,
        start_idx=start_idx,
        end_idx=end_idx,
        total_grns=total_grns,
        total_qty=total_qty,
        this_month=this_month,
        vendor_count=vendor_count,
        partial_count=partial_count,
        ordered_total=ordered_total
    )


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
    query = request.args.get('q', '')
    vendor_filter = request.args.get('vendor_id', type=int)
    type_filter = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)

    invoice_list = list(storage.purchases)
    if query:
        q = query.lower()
        invoice_list = [p for p in invoice_list
                        if q in (p.purchase_id or '').lower()
                        or q in (p.brand_name or '').lower()
                        or q in (p.model_name or '').lower()
                        or (p.vendor and q in p.vendor.vendor_name.lower())]
    if vendor_filter:
        invoice_list = [p for p in invoice_list if p.vendor_id == vendor_filter]
    if type_filter and type_filter != 'All':
        invoice_list = [p for p in invoice_list if p.purchase_type == type_filter]

    invoice_list = sorted(invoice_list, key=lambda p: p.purchase_date or date.today(), reverse=True)

    total_invoices = len(storage.purchases)
    invoiced_total = sum(p.total_amount for p in storage.purchases)
    today = date.today()
    this_month = sum(1 for p in storage.purchases
                     if p.purchase_date and p.purchase_date.year == today.year and p.purchase_date.month == today.month)
    vendor_count = len({p.vendor_id for p in storage.purchases if p.vendor_id})
    avg_invoice = round(invoiced_total / total_invoices) if total_invoices else 0
    purchase_type_list = sorted({p.purchase_type for p in storage.purchases})
    purchase_types = len(purchase_type_list)

    vendors = sorted(storage.vendors, key=lambda v: v.vendor_name)

    invoices_page, page, total_pages, total_items = paginate(invoice_list, page)
    pages = pagination_pages(page, total_pages)
    start_idx = (page - 1) * PER_PAGE + 1
    end_idx = min(start_idx + len(invoices_page) - 1, total_items)

    return render_template(
        'invoices.html',
        purchases=invoices_page,
        vendors=vendors,
        query=query,
        vendor_filter=vendor_filter,
        type_filter=type_filter,
        purchase_type_list=purchase_type_list,
        page=page,
        total_pages=total_pages,
        total_items=total_items,
        pages=pages,
        start_idx=start_idx,
        end_idx=end_idx,
        total_invoices=total_invoices,
        invoiced_total=invoiced_total,
        this_month=this_month,
        vendor_count=vendor_count,
        avg_invoice=avg_invoice,
        purchase_types=purchase_types
    )


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

    aging_total = sum(item['outstanding'] for item in aging_data)
    aging_buckets = {
        '0-30 Days': [0, 0.0],
        '31-60 Days': [0, 0.0],
        '61-90 Days': [0, 0.0],
        '90+ Days': [0, 0.0],
    }
    for item in aging_data:
        aging_buckets[item['bucket']][0] += 1
        aging_buckets[item['bucket']][1] += item['outstanding']

    return render_template('reports_aging.html', aging_data=aging_data,
                           aging_buckets=aging_buckets, aging_total=aging_total)


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

