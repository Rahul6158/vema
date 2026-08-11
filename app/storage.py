"""SQLite-backed application storage.

The previous implementation wrote every collection to JSON files under a
``google_drive`` directory.  This adapter deliberately preserves the small
storage API used by the routes while storing the data in one SQLite database.
"""
import os
import sqlite3
from datetime import date, datetime
from typing import Any, List

from .models import (Brand, Category, Customer, Offer, OfferMessage, Payment, Product,
                     Purchase, PurchaseItem, Role, StoreSetting, User, Vendor,
                     Warranty, WhatsAppMessage)


COLLECTIONS = {
    'roles': ('role', Role), 'users': ('user', User),
    'customers': ('customer', Customer), 'vendors': ('vendor', Vendor),
    'categories': ('category', Category), 'brands': ('brand', Brand),
    'products': ('product', Product), 'purchases': ('purchase', Purchase),
    'payments': ('payment', Payment),
    'purchase_items': ('purchase_item', PurchaseItem),
    'warranties': ('warranty', Warranty),
    'whatsapp_messages': ('whats_app_message', WhatsAppMessage),
    'offers': ('offer', Offer), 'offer_messages': ('offer_message', OfferMessage),
    'settings': ('store_setting', StoreSetting),
}


class SQLiteStorage:
    def __init__(self, database_path=None):
        self.database_path = database_path or os.environ.get(
            'DATABASE_PATH', os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'data.db')))
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        self._create_schema()
        self.ensure_data()

    def _connect(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_schema(self):
        # Core tables may already exist from earlier versions.  These tables
        # are idempotent and only fill in the features that were not present.
        with self._connect() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS role (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS user (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, phone TEXT, password_hash TEXT NOT NULL, role_id INTEGER, active INTEGER DEFAULT 1, created_at TEXT, FOREIGN KEY(role_id) REFERENCES role(id));
                CREATE TABLE IF NOT EXISTS customer (id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT, town TEXT, district TEXT, created_at TEXT);
                CREATE TABLE IF NOT EXISTS vendor (id INTEGER PRIMARY KEY, vendor_name TEXT NOT NULL, phone TEXT, state TEXT, city TEXT, created_at TEXT, updated_at TEXT);
                CREATE TABLE IF NOT EXISTS category (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS brand (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS product (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category_id INTEGER, brand_id INTEGER, model TEXT, capacity TEXT, sku TEXT, purchase_price REAL, selling_price REAL, stock INTEGER, warranty_months INTEGER, active INTEGER DEFAULT 1, FOREIGN KEY(category_id) REFERENCES category(id), FOREIGN KEY(brand_id) REFERENCES brand(id));
                CREATE TABLE IF NOT EXISTS purchase (id INTEGER PRIMARY KEY, purchase_id TEXT NOT NULL, vendor_id INTEGER, brand_name TEXT, model_name TEXT, quantity INTEGER, purchase_date TEXT, unit_price REAL, total_amount REAL, attachment TEXT, created_at TEXT, customer_id INTEGER, user_id INTEGER, purchase_type TEXT, subtotal REAL, total REAL, FOREIGN KEY(vendor_id) REFERENCES vendor(id));
                CREATE TABLE IF NOT EXISTS payment (id INTEGER PRIMARY KEY, vendor_id INTEGER NOT NULL, payment_date TEXT, payment_method TEXT, amount_paid REAL, attachment TEXT, created_at TEXT, FOREIGN KEY(vendor_id) REFERENCES vendor(id));
                CREATE TABLE IF NOT EXISTS purchase_item (id INTEGER PRIMARY KEY, purchase_id INTEGER, product_id INTEGER, brand TEXT, model TEXT, capacity TEXT, qty INTEGER, price REAL, total REAL, FOREIGN KEY(purchase_id) REFERENCES purchase(id), FOREIGN KEY(product_id) REFERENCES product(id));
                CREATE TABLE IF NOT EXISTS warranty (id INTEGER PRIMARY KEY, purchase_id INTEGER, applicable INTEGER, duration TEXT, start_date TEXT, end_date TEXT, document TEXT, FOREIGN KEY(purchase_id) REFERENCES purchase(id));
                CREATE TABLE IF NOT EXISTS whats_app_message (id INTEGER PRIMARY KEY, purchase_id INTEGER, message_id TEXT, status TEXT, sent_at TEXT, error TEXT, FOREIGN KEY(purchase_id) REFERENCES purchase(id));
                CREATE TABLE IF NOT EXISTS offer (id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT, product_ids TEXT, start_date TEXT, end_date TEXT, active INTEGER DEFAULT 1, image TEXT, message TEXT);
                CREATE TABLE IF NOT EXISTS offer_message (id INTEGER PRIMARY KEY, offer_id INTEGER, customer_id INTEGER, status TEXT, sent_at TEXT, error TEXT, FOREIGN KEY(offer_id) REFERENCES offer(id), FOREIGN KEY(customer_id) REFERENCES customer(id));
                CREATE TABLE IF NOT EXISTS store_setting (id INTEGER PRIMARY KEY, "key" TEXT NOT NULL UNIQUE, value TEXT);
            ''')
            cols = [r['name'] for r in conn.execute('PRAGMA table_info(purchase)').fetchall()]
            new_cols = [
                ('vendor_id', 'INTEGER'), ('brand_name', 'TEXT'), ('model_name', 'TEXT'),
                ('quantity', 'INTEGER'), ('purchase_date', 'TEXT'), ('unit_price', 'REAL'),
                ('total_amount', 'REAL'), ('attachment', 'TEXT')
            ]
            for col_name, col_type in new_cols:
                if col_name not in cols:
                    try:
                        conn.execute(f'ALTER TABLE purchase ADD COLUMN {col_name} {col_type}')
                    except Exception:
                        pass

    def ensure_data(self):
        for name, (table, cls) in COLLECTIONS.items():
            rows = self._connect().execute(f'SELECT * FROM "{table}"').fetchall()
            values = []
            for row in rows:
                item = dict(row)
                if name == 'offers':
                    import json
                    item['product_ids'] = json.loads(item.get('product_ids') or '[]')
                obj = cls.from_dict(item, storage=self)
                if hasattr(obj, '_storage'):
                    obj._storage = self
                values.append(obj)
            setattr(self, name, values)

    def _next_id(self, items):
        return max((item.id or 0 for item in items), default=0) + 1

    @staticmethod
    def _value(value: Any):
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, bool):
            return int(value)
        return value

    def _save_collection(self, name):
        import json
        table, _ = COLLECTIONS[name]
        items = getattr(self, name)
        with self._connect() as conn:
            conn.execute(f'DELETE FROM "{table}"')
            for obj in items:
                data = obj.to_dict()
                if name == 'offers':
                    data['product_ids'] = json.dumps(data['product_ids'])
                cols = list(data.keys())
                placeholders = ', '.join('?' for _ in cols)
                conn.execute(f'INSERT INTO "{table}" ({", ".join(chr(34)+c+chr(34) for c in cols)}) VALUES ({placeholders})',
                             [self._value(data[c]) for c in cols])

    def save_all(self):
        for name in COLLECTIONS: self._save_collection(name)

    def __getattr__(self, name):
        if name.startswith('save_') and name[5:] in COLLECTIONS:
            return lambda: self._save_collection(name[5:])
        raise AttributeError(name)

    def _get(self, collection, item_id):
        return next((x for x in getattr(self, collection) if x.id == item_id), None)
    def get_role(self, id): return self._get('roles', id)
    def get_user(self, id): return self._get('users', id)
    def get_customer(self, id): return self._get('customers', id)
    def get_vendor(self, id): return self._get('vendors', id)
    def get_category(self, id): return self._get('categories', id)
    def get_brand(self, id): return self._get('brands', id)
    def get_product(self, id): return self._get('products', id)
    def get_purchase(self, id): return self._get('purchases', id)
    def get_payment(self, id): return self._get('payments', id)
    def get_offer(self, id): return self._get('offers', id)
    def find_purchase_by_code(self, code): return next((x for x in self.purchases if x.purchase_id == code), None)
    def get_purchase_items(self, id): return [x for x in self.purchase_items if x.purchase_id == id]
    def get_warranty(self, id): return next((x for x in self.warranties if x.purchase_id == id), None)
    def get_whatsapp_messages(self, id): return [x for x in self.whatsapp_messages if x.purchase_id == id]
    def get_offer_messages(self, id): return [x for x in self.offer_messages if x.offer_id == id]

    def _find_name(self, collection, value):
        return next((x for x in getattr(self, collection) if getattr(x, 'name', '').lower() == (value or '').lower()), None)
    def find_role_by_name(self, value): return self._find_name('roles', value)
    def find_category_by_name(self, value): return self._find_name('categories', value)
    def find_brand_by_name(self, value): return self._find_name('brands', value)
    def find_user_by_email(self, value): return next((x for x in self.users if x.email.lower() == (value or '').lower()), None)
    def find_customer_by_phone(self, value): return next((x for x in self.customers if x.phone == value), None)
    def find_vendor_by_name(self, value): return next((x for x in self.vendors if x.vendor_name.lower() == (value or '').lower()), None)
    def get_setting(self, key, default=''):
        item = next((x for x in self.settings if x.key == key), None)
        return item.value if item else default
    def set_setting(self, key, value):
        item = next((x for x in self.settings if x.key == key), None)
        if item: item.value = value
        else: self.add_setting(StoreSetting(key=key, value=value))
        self.save_settings()
    def active_products(self): return [x for x in self.products if x.active]
    def search_customers(self, query):
        q=(query or '').lower(); return [x for x in self.customers if q in x.name.lower() or q in x.phone.lower()]
    def search_vendors(self, query):
        q=(query or '').lower(); return [x for x in self.vendors if q in x.vendor_name.lower() or q in (x.phone or '').lower() or q in (x.city or '').lower() or q in (x.state or '').lower()]
    def search_products(self, query):
        q=(query or '').lower(); return [x for x in self.products if q in x.name.lower() or q in (x.model or '').lower()]
    def search_purchases(self, query):
        q=(query or '').lower(); return [x for x in self.purchases if q in x.purchase_id.lower() or q in (x.brand_name or '').lower() or q in (x.model_name or '').lower()]
    def search_payments(self, query):
        q=(query or '').lower(); return [x for x in self.payments if q in (x.payment_method or '').lower() or (x.vendor and q in x.vendor.vendor_name.lower())]
    def recent_customers(self, limit=5): return sorted(self.customers, key=lambda x:x.created_at, reverse=True)[:limit]
    def recent_vendors(self, limit=5): return sorted(self.vendors, key=lambda x:x.created_at, reverse=True)[:limit]
    def recent_purchases(self, limit=5): return sorted(self.purchases, key=lambda x:x.created_at, reverse=True)[:limit]
    def recent_payments(self, limit=5): return sorted(self.payments, key=lambda x:x.created_at, reverse=True)[:limit]

    def _add(self, collection, obj):
        items=getattr(self, collection); obj.id=self._next_id(items)
        if hasattr(obj, '_storage'): obj._storage=self
        items.append(obj); self._save_collection(collection); return obj
    def add_role(self, x): return self._add('roles', x)
    def add_user(self, x): return self._add('users', x)
    def add_customer(self, x): return self._add('customers', x)
    def add_vendor(self, x): return self._add('vendors', x)
    def add_category(self, x): return self._add('categories', x)
    def add_brand(self, x): return self._add('brands', x)
    def add_product(self, x): return self._add('products', x)
    def add_purchase(self, x): return self._add('purchases', x)
    def add_payment(self, x): return self._add('payments', x)
    def add_purchase_item(self, x): return self._add('purchase_items', x)
    def add_warranty(self, x): return self._add('warranties', x)
    def add_whatsapp_message(self, x): return self._add('whatsapp_messages', x)
    def add_offer(self, x): return self._add('offers', x)
    def add_offer_message(self, x): return self._add('offer_messages', x)
    def add_setting(self, x): return self._add('settings', x)


storage = SQLiteStorage()
