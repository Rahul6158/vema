from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import login_manager


def _parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.utcnow()
    return datetime.utcnow()


def _parse_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


class Role:
    def __init__(self, id=None, name=''):
        self.id = id
        self.name = name

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

    @classmethod
    def from_dict(cls, data, storage=None):
        return cls(id=data.get('id'), name=data.get('name', ''))


class User(UserMixin):
    def __init__(self, id=None, name='', email='', phone='', password_hash='', role_id=None, active=True, created_at=None):
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.password_hash = password_hash
        self.role_id = role_id
        self.active = active
        self.created_at = _parse_datetime(created_at)
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def role(self):
        if self._storage and self.role_id is not None:
            return self._storage.get_role(self.role_id)
        return None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'password_hash': self.password_hash,
            'role_id': self.role_id,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        user = cls(
            id=data.get('id'),
            name=data.get('name', ''),
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            password_hash=data.get('password_hash', ''),
            role_id=data.get('role_id'),
            active=data.get('active', True),
            created_at=data.get('created_at')
        )
        user._storage = storage
        return user


class Customer:
    def __init__(self, id=None, name='', phone='', email='', town='', district='', created_at=None):
        self.id = id
        self.name = name
        self.phone = phone
        self.email = email
        self.town = town
        self.district = district
        self.created_at = _parse_datetime(created_at)
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def purchases(self):
        if self._storage:
            return [purchase for purchase in self._storage.purchases if purchase.customer_id == self.id]
        return []

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'town': self.town,
            'district': self.district,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        customer = cls(
            id=data.get('id'),
            name=data.get('name', ''),
            phone=data.get('phone', ''),
            email=data.get('email', ''),
            town=data.get('town', ''),
            district=data.get('district', ''),
            created_at=data.get('created_at')
        )
        customer._storage = storage
        return customer


class Category:
    def __init__(self, id=None, name=''):
        self.id = id
        self.name = name

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

    @classmethod
    def from_dict(cls, data, storage=None):
        return cls(id=data.get('id'), name=data.get('name', ''))


class Brand:
    def __init__(self, id=None, name=''):
        self.id = id
        self.name = name

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

    @classmethod
    def from_dict(cls, data, storage=None):
        return cls(id=data.get('id'), name=data.get('name', ''))


class Product:
    def __init__(self, id=None, name='', category_id=None, brand_id=None, model='', capacity='', sku='', purchase_price=0, selling_price=0, stock=0, warranty_months=0, active=True):
        self.id = id
        self.name = name
        self.category_id = category_id
        self.brand_id = brand_id
        self.model = model
        self.capacity = capacity
        self.sku = sku
        self.purchase_price = float(purchase_price or 0)
        self.selling_price = float(selling_price or 0)
        self.stock = int(stock or 0)
        self.warranty_months = int(warranty_months or 0)
        self.active = bool(active)
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def category(self):
        if self._storage and self.category_id is not None:
            return self._storage.get_category(self.category_id)
        return None

    @property
    def brand(self):
        if self._storage and self.brand_id is not None:
            return self._storage.get_brand(self.brand_id)
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'brand_id': self.brand_id,
            'model': self.model,
            'capacity': self.capacity,
            'sku': self.sku,
            'purchase_price': self.purchase_price,
            'selling_price': self.selling_price,
            'stock': self.stock,
            'warranty_months': self.warranty_months,
            'active': self.active,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        product = cls(
            id=data.get('id'),
            name=data.get('name', ''),
            category_id=data.get('category_id'),
            brand_id=data.get('brand_id'),
            model=data.get('model', ''),
            capacity=data.get('capacity', ''),
            sku=data.get('sku', ''),
            purchase_price=data.get('purchase_price', 0),
            selling_price=data.get('selling_price', 0),
            stock=data.get('stock', 0),
            warranty_months=data.get('warranty_months', 0),
            active=data.get('active', True)
        )
        product._storage = storage
        return product


class GoodsReceived:
    def __init__(self, id=None, grn_number='', purchase_id=None, received_date=None,
                 received_qty=0, condition_notes='', received_by='', created_at=None):
        self.id = id
        self.grn_number = grn_number or ''
        self.purchase_id = purchase_id
        self.received_date = _parse_date(received_date) or date.today()
        self.received_qty = int(received_qty or 0)
        self.condition_notes = condition_notes or ''
        self.received_by = received_by or ''
        self.created_at = _parse_datetime(created_at)
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def purchase(self):
        if self._storage and self.purchase_id is not None:
            return self._storage.get_purchase(self.purchase_id)
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'grn_number': self.grn_number,
            'purchase_id': self.purchase_id,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'received_qty': self.received_qty,
            'condition_notes': self.condition_notes,
            'received_by': self.received_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        grn = cls(
            id=data.get('id'),
            grn_number=data.get('grn_number', ''),
            purchase_id=data.get('purchase_id'),
            received_date=data.get('received_date'),
            received_qty=data.get('received_qty', 0),
            condition_notes=data.get('condition_notes', ''),
            received_by=data.get('received_by', ''),
            created_at=data.get('created_at')
        )
        grn._storage = storage
        return grn


class Vendor:
    def __init__(self, id=None, vendor_name='', phone='', state='', city='',
                 contact_person='', vendor_type='', status='Active',
                 gst_number='', pan_number='', bank_account='', ifsc_code='',
                 created_at=None, updated_at=None):
        self.id = id
        self.vendor_name = vendor_name
        self.phone = phone
        self.state = state
        self.city = city
        self.contact_person = contact_person or ''
        self.vendor_type = vendor_type or ''
        self.status = status or 'Active'
        self.gst_number = gst_number or ''
        self.pan_number = pan_number or ''
        self.bank_account = bank_account or ''
        self.ifsc_code = ifsc_code or ''
        self.created_at = _parse_datetime(created_at)
        self.updated_at = _parse_datetime(updated_at) if updated_at else self.created_at
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def name(self):
        return self.vendor_name

    @property
    def purchases(self):
        if self._storage:
            return [p for p in self._storage.purchases if p.vendor_id == self.id]
        return []

    @property
    def payments(self):
        if self._storage:
            return [p for p in self._storage.payments if p.vendor_id == self.id]
        return []

    @property
    def total_purchased(self):
        return sum(p.total_amount for p in self.purchases)

    @property
    def total_paid(self):
        return sum(p.amount_paid for p in self.payments)

    @property
    def payment_balance(self):
        # Outstanding Balance = Total Purchase Value - Total Payments Made
        return self.total_purchased - self.total_paid

    @property
    def outstanding_balance(self):
        return self.payment_balance

    @property
    def last_payment(self):
        pmts = sorted(self.payments, key=lambda p: p.payment_date or p.created_at, reverse=True)
        if pmts:
            latest = pmts[0]
            dt_str = latest.payment_date.strftime('%Y-%m-%d') if isinstance(latest.payment_date, (date, datetime)) else str(latest.payment_date or '')
            return f"₹{latest.amount_paid:,.2f} ({latest.payment_method}) on {dt_str}"
        return "No payments yet"

    @property
    def last_payment_date(self):
        pmts = sorted(self.payments, key=lambda p: p.payment_date or p.created_at, reverse=True)
        return pmts[0].payment_date if pmts else None

    def to_dict(self):
        return {
            'id': self.id,
            'vendor_name': self.vendor_name,
            'phone': self.phone,
            'state': self.state,
            'city': self.city,
            'contact_person': self.contact_person,
            'vendor_type': self.vendor_type,
            'status': self.status,
            'gst_number': self.gst_number,
            'pan_number': self.pan_number,
            'bank_account': self.bank_account,
            'ifsc_code': self.ifsc_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        vendor = cls(
            id=data.get('id'),
            vendor_name=data.get('vendor_name', ''),
            phone=data.get('phone', ''),
            state=data.get('state', ''),
            city=data.get('city', ''),
            contact_person=data.get('contact_person', ''),
            vendor_type=data.get('vendor_type', ''),
            status=data.get('status', 'Active'),
            gst_number=data.get('gst_number', ''),
            pan_number=data.get('pan_number', ''),
            bank_account=data.get('bank_account', ''),
            ifsc_code=data.get('ifsc_code', ''),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
        vendor._storage = storage
        return vendor



class Payment:
    def __init__(self, id=None, vendor_id=None, payment_date=None, payment_method='Cash',
                 amount_paid=0, attachment='', reference_number='', notes='', created_at=None):
        self.id = id
        self.vendor_id = vendor_id
        self.payment_date = _parse_date(payment_date) or date.today()
        self.payment_method = payment_method or 'Cash'
        self.amount_paid = float(amount_paid or 0)
        self.attachment = attachment or ''
        self.reference_number = reference_number or ''
        self.notes = notes or ''
        self.created_at = _parse_datetime(created_at)
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def vendor(self):
        if self._storage and self.vendor_id is not None:
            return self._storage.get_vendor(self.vendor_id)
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'payment_method': self.payment_method,
            'amount_paid': self.amount_paid,
            'attachment': self.attachment,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        pmt = cls(
            id=data.get('id'),
            vendor_id=data.get('vendor_id'),
            payment_date=data.get('payment_date'),
            payment_method=data.get('payment_method', 'Cash'),
            amount_paid=data.get('amount_paid', 0),
            attachment=data.get('attachment', ''),
            reference_number=data.get('reference_number', ''),
            notes=data.get('notes', ''),
            created_at=data.get('created_at')
        )
        pmt._storage = storage
        return pmt


class Purchase:
    def __init__(self, id=None, purchase_id='', vendor_id=None, brand_name='', model_name='', quantity=1, purchase_date=None, unit_price=0, total_amount=0, attachment='', created_at=None, customer_id=None, user_id=None, purchase_type='Retail', subtotal=0, total=0, status='Approved'):
        self.id = id
        self.purchase_id = purchase_id
        self.vendor_id = vendor_id
        self.brand_name = brand_name
        self.model_name = model_name
        self.quantity = int(quantity or 1)
        self.purchase_date = _parse_date(purchase_date) or date.today()
        self.unit_price = float(unit_price or 0)
        
        tot = float(total_amount or total or 0)
        if tot == 0 and self.quantity > 0 and self.unit_price > 0:
            tot = self.quantity * self.unit_price
        self.total_amount = tot
        self.attachment = attachment or ''
        self.created_at = _parse_datetime(created_at)
        
        # Legacy/Extra compatibility fields
        self.customer_id = customer_id
        self.user_id = user_id
        self.purchase_type = purchase_type
        self.subtotal = float(subtotal or tot)
        self.total = tot
        self.status = status or 'Approved'
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def vendor(self):
        if self._storage and self.vendor_id is not None:
            return self._storage.get_vendor(self.vendor_id)
        return None

    @property
    def customer(self):
        if self._storage and self.customer_id is not None:
            return self._storage.get_customer(self.customer_id)
        return None

    @property
    def user(self):
        if self._storage and self.user_id is not None:
            return self._storage.get_user(self.user_id)
        return None

    @property
    def items(self):
        if self._storage:
            return self._storage.get_purchase_items(self.id)
        return []

    @property
    def warranty(self):
        if self._storage:
            return self._storage.get_warranty(self.id)
        return None

    @property
    def whatsapp_messages(self):
        if self._storage:
            return self._storage.get_whatsapp_messages(self.id)
        return []

    def to_dict(self):
        return {
            'id': self.id,
            'purchase_id': self.purchase_id,
            'vendor_id': self.vendor_id,
            'brand_name': self.brand_name,
            'model_name': self.model_name,
            'quantity': self.quantity,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'unit_price': self.unit_price,
            'total_amount': self.total_amount,
            'attachment': self.attachment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'customer_id': self.customer_id,
            'user_id': self.user_id,
            'purchase_type': self.purchase_type,
            'subtotal': self.subtotal,
            'total': self.total,
            'status': self.status,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        purchase = cls(
            id=data.get('id'),
            purchase_id=data.get('purchase_id', ''),
            vendor_id=data.get('vendor_id'),
            brand_name=data.get('brand_name', ''),
            model_name=data.get('model_name', ''),
            quantity=data.get('quantity', 1),
            purchase_date=data.get('purchase_date'),
            unit_price=data.get('unit_price', 0),
            total_amount=data.get('total_amount', 0),
            attachment=data.get('attachment', ''),
            created_at=data.get('created_at'),
            customer_id=data.get('customer_id'),
            user_id=data.get('user_id'),
            purchase_type=data.get('purchase_type', 'Retail'),
            subtotal=data.get('subtotal', 0),
            total=data.get('total', 0),
            status=data.get('status', 'Approved')
        )
        purchase._storage = storage
        return purchase


class PurchaseItem:
    def __init__(self, id=None, purchase_id=None, product_id=None, brand='', model='', capacity='', qty=1, price=0, total=0):
        self.id = id
        self.purchase_id = purchase_id
        self.product_id = product_id
        self.brand = brand
        self.model = model
        self.capacity = capacity
        self.qty = int(qty or 1)
        self.price = float(price or 0)
        self.total = float(total or 0)
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def product(self):
        if self._storage and self.product_id is not None:
            return self._storage.get_product(self.product_id)
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'purchase_id': self.purchase_id,
            'product_id': self.product_id,
            'brand': self.brand,
            'model': self.model,
            'capacity': self.capacity,
            'qty': self.qty,
            'price': self.price,
            'total': self.total,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        item = cls(
            id=data.get('id'),
            purchase_id=data.get('purchase_id'),
            product_id=data.get('product_id'),
            brand=data.get('brand', ''),
            model=data.get('model', ''),
            capacity=data.get('capacity', ''),
            qty=data.get('qty', 1),
            price=data.get('price', 0),
            total=data.get('total', 0)
        )
        item._storage = storage
        return item


class Warranty:
    def __init__(self, id=None, purchase_id=None, applicable=False, duration='', start_date=None, end_date=None, document=''):
        self.id = id
        self.purchase_id = purchase_id
        self.applicable = bool(applicable)
        self.duration = duration
        self.start_date = _parse_date(start_date)
        self.end_date = _parse_date(end_date)
        self.document = document

    def to_dict(self):
        return {
            'id': self.id,
            'purchase_id': self.purchase_id,
            'applicable': self.applicable,
            'duration': self.duration,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'document': self.document,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        return cls(
            id=data.get('id'),
            purchase_id=data.get('purchase_id'),
            applicable=data.get('applicable', False),
            duration=data.get('duration', ''),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            document=data.get('document', '')
        )


class WhatsAppMessage:
    def __init__(self, id=None, purchase_id=None, message_id='', status='Not Sent', sent_at=None, error=''):
        self.id = id
        self.purchase_id = purchase_id
        self.message_id = message_id
        self.status = status
        self.sent_at = _parse_datetime(sent_at) if sent_at else None
        self.error = error

    def to_dict(self):
        return {
            'id': self.id,
            'purchase_id': self.purchase_id,
            'message_id': self.message_id,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'error': self.error,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        return cls(
            id=data.get('id'),
            purchase_id=data.get('purchase_id'),
            message_id=data.get('message_id', ''),
            status=data.get('status', 'Not Sent'),
            sent_at=data.get('sent_at'),
            error=data.get('error', '')
        )


class Offer:
    def __init__(self, id=None, title='', description='', product_ids=None, start_date=None, end_date=None, active=True, image='', message=''):
        self.id = id
        self.title = title
        self.description = description
        self.product_ids = product_ids or []
        self.start_date = _parse_date(start_date)
        self.end_date = _parse_date(end_date)
        self.active = bool(active)
        self.image = image or ''
        self.message = message or ''
        self._storage = None

    def set_storage(self, storage):
        self._storage = storage

    @property
    def products(self):
        if self._storage:
            return [self._storage.get_product(int(pid)) for pid in self.product_ids if pid is not None and self._storage.get_product(int(pid))]
        return []

    @property
    def is_current(self):
        today = date.today()
        return self.active and self.start_date and self.end_date and self.start_date <= today <= self.end_date

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'product_ids': self.product_ids,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'active': self.active,
            'image': self.image,
            'message': self.message,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        offer = cls(
            id=data.get('id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            product_ids=data.get('product_ids', []) or [],
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            active=data.get('active', True),
            image=data.get('image', ''),
            message=data.get('message', '')
        )
        offer._storage = storage
        return offer


class OfferMessage:
    def __init__(self, id=None, offer_id=None, customer_id=None, status='Not Sent', sent_at=None, error=''):
        self.id = id
        self.offer_id = offer_id
        self.customer_id = customer_id
        self.status = status
        self.sent_at = _parse_datetime(sent_at) if sent_at else None
        self.error = error

    def to_dict(self):
        return {
            'id': self.id,
            'offer_id': self.offer_id,
            'customer_id': self.customer_id,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'error': self.error,
        }

    @classmethod
    def from_dict(cls, data, storage=None):
        return cls(
            id=data.get('id'),
            offer_id=data.get('offer_id'),
            customer_id=data.get('customer_id'),
            status=data.get('status', 'Not Sent'),
            sent_at=data.get('sent_at'),
            error=data.get('error', '')
        )


class StoreSetting:
    def __init__(self, id=None, key='', value=''):
        self.id = id
        self.key = key
        self.value = value

    def to_dict(self):
        return {'id': self.id, 'key': self.key, 'value': self.value}

    @classmethod
    def from_dict(cls, data, storage=None):
        return cls(id=data.get('id'), key=data.get('key', ''), value=data.get('value', ''))


@login_manager.user_loader
def load_user(user_id):
    from .storage import storage
    try:
        return storage.get_user(int(user_id))
    except (TypeError, ValueError):
        return None
