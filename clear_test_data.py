"""Clear all test transactions, test purchases, test payments, and test GRNs from database to keep it clean.

Run from project root:
    python clear_test_data.py
"""
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.storage import storage

def clear_test_data():
    print("Clearing test transactions from database...")
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

    print("Successfully cleared all test transactions!")
    print(f"Remaining Masters:")
    print(f"  Brands: {len(storage.brands)}")
    print(f"  Categories: {len(storage.categories)}")
    print(f"  Products: {len(storage.products)}")
    print(f"  Vendors: {len(storage.vendors)}")
    print(f"  Users: {len(storage.users)}")

if __name__ == '__main__':
    clear_test_data()
