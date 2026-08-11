from app import create_app
from app.storage import storage

app = create_app()
with app.app_context():
    storage.ensure_data()
    client = app.test_client()
    
    # Login as admin
    admin = storage.find_user_by_email('admin@example.com')
    client.post('/login', data={'email': 'admin@example.com', 'password': 'adminpass'}, follow_redirects=True)

    vendor = storage.vendors[0] if storage.vendors else None
    print("Testing vendor:", vendor.vendor_name if vendor else None)

    # 1. Test POST /purchases/add
    res_pur = client.post('/purchases/add', data={
        'vendor_id': vendor.id if vendor else 1,
        'brand_name': 'Samsung',
        'model_name': 'Test Model',
        'quantity': '2',
        'unit_price': '15000',
        'purchase_date': '2026-08-12'
    }, follow_redirects=True)
    print("POST /purchases/add Status:", res_pur.status_code)
    if res_pur.status_code != 200:
        print("Response data:", res_pur.data.decode('utf-8')[:500])

    # 2. Test POST /payments/add
    res_pmt = client.post('/payments/add', data={
        'vendor_id': vendor.id if vendor else 1,
        'payment_date': '2026-08-12',
        'payment_method': 'UPI',
        'amount_paid': '10000'
    }, follow_redirects=True)
    print("POST /payments/add Status:", res_pmt.status_code)
    if res_pmt.status_code != 200:
        print("Response data:", res_pmt.data.decode('utf-8')[:500])
