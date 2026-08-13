import os
import uuid
from datetime import date
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.storage import storage
from app.models import Vendor, Purchase, Payment

def test_vendor_crm():
    print("--- STARTING VENDOR MANAGEMENT CRM VALIDATION ---")
    app = create_app()
    with app.app_context():
        storage.ensure_data()
        
        # 1. Register test vendor (Apex Electronics)
        vendor_name = "Apex Electronics Ltd"
        vendor = storage.find_vendor_by_name(vendor_name)
        if not vendor:
            vendor = storage.add_vendor(Vendor(vendor_name=vendor_name, phone="9876543210", state="Maharashtra", city="Mumbai"))
            print(f"[OK] Vendor Created: {vendor.vendor_name} (ID: {vendor.id})")
        else:
            print(f"[INFO] Vendor Found: {vendor.vendor_name} (ID: {vendor.id})")

        # 2. Test PRD Section 10 Core Business Logic
        storage.purchases = [p for p in storage.purchases if p.vendor_id != vendor.id]
        storage.payments = [p for p in storage.payments if p.vendor_id != vendor.id]
        storage.save_purchases()
        storage.save_payments()

        test_code = f"PUR-TEST-{uuid.uuid4().hex[:6]}"
        pur1 = Purchase(
            purchase_id=test_code,
            vendor_id=vendor.id,
            brand_name="Samsung",
            model_name="Display Panel X",
            quantity=10,
            purchase_date=date.today().isoformat(),
            unit_price=10000,
            total_amount=100000
        )
        storage.add_purchase(pur1)
        print(f"[OK] Purchase Added: {pur1.purchase_id} | Total: Rs.{pur1.total_amount:,.2f}")

        bal1 = vendor.outstanding_balance
        print(f"[VERIFY] Balance after Purchase 1,00,000: Rs.{bal1:,.2f}")

        pmt1 = Payment(
            vendor_id=vendor.id,
            payment_date=date.today().isoformat(),
            payment_method="UPI",
            amount_paid=40000
        )
        storage.add_payment(pmt1)
        print(f"[OK] Payment 1 Added: Rs.{pmt1.amount_paid:,.2f} ({pmt1.payment_method})")

        bal2 = vendor.outstanding_balance
        print(f"[VERIFY] Balance after Payment 40,000: Rs.{bal2:,.2f}")
        assert bal2 == 60000.0, f"Expected 60,000, got {bal2}"

        pmt2 = Payment(
            vendor_id=vendor.id,
            payment_date=date.today().isoformat(),
            payment_method="Bank Transfer",
            amount_paid=20000
        )
        storage.add_payment(pmt2)
        print(f"[OK] Payment 2 Added: Rs.{pmt2.amount_paid:,.2f} ({pmt2.payment_method})")

        bal3 = vendor.outstanding_balance
        print(f"[VERIFY] Balance after Payment 20,000: Rs.{bal3:,.2f}")
        assert bal3 == 40000.0, f"Expected 40,000, got {bal3}"

        print("[SUCCESS] Core Business Logic (PRD Section 10) verified perfectly!")

        # 3. Test HTTP routes using Flask Test Client
        client = app.test_client()
        with client:
            admin = storage.find_user_by_email('admin@example.com')
            if not admin:
                from app.models import Role, User
                admin_role = storage.add_role(Role(name='Admin'))
                admin = User(name='Administrator', email='admin@example.com', phone='0000000000', role_id=admin_role.id)
                admin.set_password('adminpass')
                storage.add_user(admin)

            login_res = client.post('/login', data={'email': 'admin@example.com', 'password': 'adminpass'}, follow_redirects=True)
            print(f"[HTTP] Login response status: {login_res.status_code}")

            routes_to_test = [
                '/',
                '/vendors',
                f'/vendors/{vendor.id}',
                f'/vendors/{vendor.id}/ledger',
                '/vendors/add',
                '/purchases',
                '/purchases/add',
                '/payments',
                '/payments/add',
                '/grn',
                '/grn/add',
                '/invoices',
                '/analytics',
                '/reports',
                '/reports/aging',
                '/reports/export',
                '/products',
                '/products/add',
                '/customers',
                '/customers/add',
                '/offers',
                '/offers/add',
                '/users',
                '/users/add',
                f'/users/{admin.id}/edit',
                '/settings',
                '/profile',
                '/change-password'
            ]


            for route in routes_to_test:
                res = client.get(route)
                print(f"[HTTP GET] {route} -> Status: {res.status_code}")
                assert res.status_code == 200, f"Failed route: {route}"

        print("--- ALL VENDOR MANAGEMENT CRM CHECKS PASSED SUCCESSFULLY ---")

if __name__ == '__main__':
    test_vendor_crm()
