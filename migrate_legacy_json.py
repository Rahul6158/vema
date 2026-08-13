"""Import the former google_drive JSON data into the SQLite database.

Run once after upgrading: ``python migrate_legacy_json.py``.
The old folder is intentionally left untouched as a backup; verify the app,
then archive or delete it when you are comfortable with the migration.
"""
import json
from pathlib import Path

from app.models import Brand, Category, Customer, Offer, OfferMessage, Product, Purchase, PurchaseItem, Role, StoreSetting, User, Warranty, WhatsAppMessage
from app.storage import storage

BASE = Path(__file__).parent / 'google_drive' / 'Home Appliance Store' / 'database'
MAPPINGS = {
    'roles': ('roles.json', Role), 'users': ('users.json', User), 'customers': ('customers.json', Customer),
    'categories': ('categories.json', Category), 'brands': ('brands.json', Brand), 'products': ('products.json', Product),
    'purchases': ('purchases.json', Purchase), 'purchase_items': ('purchase_items.json', PurchaseItem),
    'warranties': ('warranties.json', Warranty), 'whatsapp_messages': ('whatsapp_messages.json', WhatsAppMessage),
    'offers': ('offers.json', Offer), 'offer_messages': ('offer_messages.json', OfferMessage), 'settings': ('settings.json', StoreSetting),
}

for collection, (filename, cls) in MAPPINGS.items():
    source = BASE / filename
    if not source.exists():
        continue
    rows = json.loads(source.read_text(encoding='utf-8'))
    imported = [cls.from_dict(row, storage=storage) for row in rows]
    for item in imported:
        if hasattr(item, '_storage'):
            item._storage = storage
    setattr(storage, collection, imported)
    getattr(storage, f'save_{collection}')()
    print(f'Imported {len(imported)} {collection}')

print(f'Finished. SQLite database: {storage.database_path}')
