"""Clear the database and seed it with realistic synthetic data.

Run from the project root:

    python seed_data.py

WARNING: This deletes ALL existing records in the SQLite database before seeding.
"""
import random
import uuid
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

from app.storage import storage, COLLECTIONS
from app.models import (
    Role, User, Customer, Category, Brand, Product,
    Vendor, Payment, Purchase, PurchaseItem, Warranty,
    WhatsAppMessage, GoodsReceived, Offer, OfferMessage, StoreSetting,
)

random.seed(42)


def reset_database():
    """Delete every row from every table, then reload the empty in-memory state."""
    import sqlite3
    conn = sqlite3.connect(storage.database_path)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for table in tables:
        conn.execute(f'DELETE FROM "{table}"')
    conn.commit()
    conn.close()
    storage.ensure_data()  # reload empty collections (also re-seeds roles)


def rand_date(start, end):
    days = (end - start).days
    return start + timedelta(days=random.randint(0, days))


def iso(dt):
    return dt.isoformat()


# ==============================================================================
# USERS
# ==============================================================================
def seed_users():
    admin = storage.find_role_by_name('Admin')
    manager = storage.find_role_by_name('Manager')
    accountant = storage.find_role_by_name('Accountant')
    staff = storage.find_role_by_name('Staff')

    def make(name, email, phone, role, password):
        u = User(name=name, email=email, phone=phone, role_id=role.id,
                 created_at=datetime.now() - timedelta(days=random.randint(30, 400)))
        u.set_password(password)
        storage.add_user(u)
        return u

    users = [
        make('VEMA Administrator', 'admin@example.com', '9876500001', admin, 'adminpass'),
        make('Rahul Sharma', 'manager@example.com', '9876500002', manager, 'manager123'),
        make('Priya Patel', 'accountant@example.com', '9876500003', accountant, 'account123'),
        make('Amit Verma', 'staff@example.com', '9876500004', staff, 'staff123'),
        make('Sneha Reddy', 'sneha@example.com', '9876500005', staff, 'staff123'),
        make('Vikram Singh', 'vikram@example.com', '9876500006', accountant, 'account123'),
    ]
    return users


# ==============================================================================
# CATEGORIES, BRANDS & PRODUCTS
# ==============================================================================
CATEGORIES = ['Fans', 'Mixer Grinders', 'Grinders', 'Gas Stoves', 'Air Coolers',
              'Water Heaters', 'Kitchen Chimneys', 'Refrigerators', 'Washing Machines',
              'LED Televisions', 'Rice Cookers']

BRANDS = ['Crompton', 'Usha', 'Preethi', 'Bajaj', 'Havells', 'Butterfly',
          'Orient Electric', 'Philips', 'LG', 'Samsung', 'Voltas', 'Pigeon',
          'Atomberg', 'Symphony', 'Prestige', 'Whirlpool', 'Elica', 'Hindware',
          'Lakshmi', 'Sunflame', 'Godrej', 'Sony', 'Mi', 'Panasonic']

PRODUCTS = [
    ('Crompton Fan 1200mm', 'Fans', 'Crompton', 'CF-1200', '1200mm', 1850, 2499, 24),
    ('Crompton Fan 1400mm', 'Fans', 'Crompton', 'CF-1400', '1400mm', 2100, 2899, 24),
    ('Usha Fan 1200mm', 'Fans', 'Usha', 'UH-1200', '1200mm', 1750, 2399, 24),
    ('Orient Electric Fan 1200mm', 'Fans', 'Orient Electric', 'OE-1200', '1200mm', 1800, 2450, 24),
    ('Havells Fan 1200mm', 'Fans', 'Havells', 'HF-1200', '1200mm', 2000, 2799, 24),
    ('Bajaj Fan 1400mm', 'Fans', 'Bajaj', 'BJ-1400', '1400mm', 1900, 2599, 24),
    ('Atomberg Renesa Fan 1200mm', 'Fans', 'Atomberg', 'AT-1200', '1200mm', 2200, 2999, 24),
    ('Preethi Mixer Blue Leaf', 'Mixer Grinders', 'Preethi', 'MG-175', '750W / 1.75L', 3100, 4499, 24),
    ('Bajaj Mixer GX 1', 'Mixer Grinders', 'Bajaj', 'MG-GX1', '500W / 1L', 2600, 3699, 24),
    ('Butterfly Mixer 750W', 'Mixer Grinders', 'Butterfly', 'BF-750', '750W / 1.5L', 2400, 3399, 24),
    ('Philips Mixer HL7756', 'Mixer Grinders', 'Philips', 'PH-HL7756', '750W / 1.75L', 2900, 3999, 24),
    ('Lakshmi Wet Grinder 2L', 'Grinders', 'Lakshmi', 'WG-2L', '2 Litre', 3200, 4599, 24),
    ('Preethi Wet Grinder 1.25L', 'Grinders', 'Preethi', 'WG-125', '1.25 Litre', 2800, 3999, 24),
    ('Sunflame Gas Stove 2 Burner', 'Gas Stoves', 'Sunflame', 'GS-2B', '2 Burner', 1800, 2599, 12),
    ('Prestige Gas Stove 2 Burner', 'Gas Stoves', 'Prestige', 'GS-P2B', '2 Burner', 2100, 2999, 12),
    ('Pigeon Gas Stove 3 Burner', 'Gas Stoves', 'Pigeon', 'GS-3B', '3 Burner', 2300, 3299, 12),
    ('Butterfly Gas Stove 4 Burner', 'Gas Stoves', 'Butterfly', 'GS-4B', '4 Burner', 2600, 3799, 12),
    ('Symphony Air Cooler 45L', 'Air Coolers', 'Symphony', 'AC-45L', '45 Litre', 5200, 7499, 12),
    ('Crompton Air Cooler 50L', 'Air Coolers', 'Crompton', 'AC-50L', '50 Litre', 5600, 7999, 12),
    ('Havells Air Cooler 55L', 'Air Coolers', 'Havells', 'AC-55L', '55 Litre', 6100, 8499, 12),
    ('Racold Geyser 15L', 'Water Heaters', 'Voltas', 'GH-15L', '15 Litre', 5200, 7499, 24),
    ('Havells Geyser 10L', 'Water Heaters', 'Havells', 'GH-10L', '10 Litre', 4200, 5999, 24),
    ('Crompton Geyser 25L', 'Water Heaters', 'Crompton', 'GH-25L', '25 Litre', 6800, 9499, 24),
    ('Elica Chimney 60cm', 'Kitchen Chimneys', 'Elica', 'KC-60', '60 cm', 6500, 9499, 24),
    ('Hindware Chimney 60cm', 'Kitchen Chimneys', 'Hindware', 'KC-H60', '60 cm', 5900, 8499, 24),
    ('LG Refrigerator 190L', 'Refrigerators', 'LG', 'RF-190', '190 Litre', 13500, 18999, 36),
    ('Samsung Refrigerator 180L', 'Refrigerators', 'Samsung', 'RF-180', '180 Litre', 12800, 17999, 36),
    ('Godrej Refrigerator 210L', 'Refrigerators', 'Godrej', 'RF-210', '210 Litre', 11200, 15999, 36),
    ('LG Washing Machine 7kg', 'Washing Machines', 'LG', 'WM-7', '7 kg', 15800, 21999, 36),
    ('Samsung Washing Machine 6.5kg', 'Washing Machines', 'Samsung', 'WM-65', '6.5 kg', 14200, 19999, 36),
    ('Whirlpool Washing Machine 8kg', 'Washing Machines', 'Whirlpool', 'WM-8', '8 kg', 16800, 23999, 36),
    ('Samsung LED TV 32"', 'LED Televisions', 'Samsung', 'TV-32', '32 inch', 14500, 19999, 36),
    ('LG LED TV 43"', 'LED Televisions', 'LG', 'TV-43', '43 inch', 23000, 31999, 36),
    ('Sony LED TV 32"', 'LED Televisions', 'Sony', 'TV-S32', '32 inch', 16800, 23999, 36),
    ('Mi LED TV 32"', 'LED Televisions', 'Mi', 'TV-32M', '32 inch', 11200, 15999, 36),
    ('Prestige Rice Cooker 1.8L', 'Rice Cookers', 'Prestige', 'RC-18', '1.8 Litre', 1300, 1999, 12),
    ('Philips Rice Cooker 1.8L', 'Rice Cookers', 'Philips', 'RC-18P', '1.8 Litre', 1500, 2299, 12),
    ('Bajaj Rice Cooker 1.8L', 'Rice Cookers', 'Bajaj', 'RC-18B', '1.8 Litre', 1200, 1849, 12),
    ('Panasonic Rice Cooker 2.5L', 'Rice Cookers', 'Panasonic', 'RC-25', '2.5 Litre', 1800, 2699, 12),
]


def seed_catalog():
    cat_map = {}
    for name in CATEGORIES:
        cat_map[name] = storage.add_category(Category(name=name))

    brand_map = {}
    for name in BRANDS:
        brand_map[name] = storage.add_brand(Brand(name=name))

    products = []
    for idx, (name, cat, brand, model, capacity, pp, sp, wmonths) in enumerate(PRODUCTS, start=1):
        p = Product(
            name=name,
            category_id=cat_map[cat].id,
            brand_id=brand_map[brand].id,
            model=model,
            capacity=capacity,
            sku=f'SKU-{brand[:3].upper()}-{idx:03d}',
            purchase_price=pp,
            selling_price=sp,
            stock=random.randint(8, 80) if idx % 7 else random.choice([0, 0, 1, 2, 3, 4, 5]),
            warranty_months=wmonths,
            active=True,
        )
        storage.add_product(p)
        products.append(p)
    return products, brand_map


# ==============================================================================
# VENDORS
# ==============================================================================
VENDORS = [
    ('Sri Venkateshwara Distributors', '9988776651', 'Telangana', 'Hyderabad', 'Suresh Kumar', 'Wholesale Distributor', 'Active'),
    ('Maa Laxmi Agencies', '9988776652', 'Karnataka', 'Bengaluru', 'Lakshmi Narayan', 'Wholesale Distributor', 'Active'),
    ('Balaji Home Appliances', '9988776653', 'Tamil Nadu', 'Chennai', 'Balaji Rao', 'Retail Supplier', 'Active'),
    ('Annapurna Trading Co.', '9988776654', 'Maharashtra', 'Pune', 'Anil Deshmukh', 'Wholesale Distributor', 'Active'),
    ('Shree Ganesh Electricals', '9988776655', 'Gujarat', 'Ahmedabad', 'Ganesh Patel', 'Retail Supplier', 'Active'),
    ('Gupta Brothers Traders', '9988776656', 'Delhi', 'New Delhi', 'Rajesh Gupta', 'Wholesale Distributor', 'Active'),
    ('Krishna Enterprise', '9988776657', 'Rajasthan', 'Jaipur', 'Krishna Meena', 'Distributor', 'Active'),
    ('Om Sai Home Solutions', '9988776658', 'West Bengal', 'Kolkata', 'Sourav Dutta', 'Wholesale Distributor', 'Active'),
    ('Vinayak Distributors', '9988776659', 'Maharashtra', 'Mumbai', 'Vinayak Joshi', 'Wholesale Distributor', 'Active'),
    ('New Bharat Electronics', '9988776660', 'Gujarat', 'Surat', 'Mahesh Shah', 'Dealer', 'Active'),
    ('Sri Lakshmi Agencies', '9988776661', 'Tamil Nadu', 'Coimbatore', 'Karthik Sundaram', 'Distributor', 'Active'),
    ('Metro Household Supplies', '9988776662', 'Kerala', 'Kochi', 'George Mathew', 'Retail Supplier', 'Active'),
]


def seed_vendors():
    vendors = []
    for idx, (name, phone, state, city, contact, vtype, status) in enumerate(VENDORS, start=1):
        created = rand_date(date.today() - timedelta(days=700), date.today() - timedelta(days=120))
        v = Vendor(
            vendor_name=name,
            phone=phone,
            state=state,
            city=city,
            contact_person=contact,
            vendor_type=vtype,
            status=status,
            gst_number=f'{random.randint(10, 39)}{random.randint(10, 99)}ABCDE{random.randint(1000, 9999)}1Z2',
            pan_number=f'{random.choice("ABCDEFGHI")}{random.choice("ABCDEFGHI")}{random.choice("ABCDEFGHI")}PS{random.randint(1000, 9999)}{random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}',
            bank_account=str(random.randint(10**10, 10**11 - 1)),
            ifsc_code=f'HBK0{random.randint(100000, 999999)}',
            created_at=created,
            updated_at=created,
        )
        storage.add_vendor(v)
        vendors.append(v)
    return vendors


# ==============================================================================
# CUSTOMERS
# ==============================================================================
CUSTOMERS = [
    ('Rajesh Kumar', '9811110001', 'Rajesh K', 'Noida', 'Gautam Buddha Nagar'),
    ('Sunita Devi', '9811110002', 'Sunita Devi', 'Ghaziabad', 'Ghaziabad'),
    ('Arun Prakash', '9811110003', 'Arun Prakash', 'Hyderabad', 'Ranga Reddy'),
    ('Meena Kumari', '9811110004', 'Meena Kumari', 'Vijayawada', 'Krishna'),
    ('Karan Malhotra', '9811110005', 'Karan Malhotra', 'Delhi', 'New Delhi'),
    ('Pooja Sharma', '9811110006', 'Pooja Sharma', 'Faridabad', 'Faridabad'),
    ('Ravi Teja', '9811110007', 'Ravi Teja', 'Bengaluru', 'Bengaluru Urban'),
    ('Anjali Desai', '9811110008', 'Anjali Desai', 'Mumbai', 'Mumbai Suburban'),
    ('Manoj Yadav', '9811110009', 'Manoj Yadav', 'Lucknow', 'Lucknow'),
    ('Divya Nair', '9811110010', 'Divya Nair', 'Kochi', 'Ernakulam'),
    ('Suresh Iyer', '9811110011', 'Suresh Iyer', 'Chennai', 'Chennai'),
    ('Kavitha Reddy', '9811110012', 'Kavitha Reddy', 'Pune', 'Pune'),
    ('Harish Gupta', '9811110013', 'Harish Gupta', 'Indore', 'Indore'),
    ('Ritu Singh', '9811110014', 'Ritu Singh', 'Jaipur', 'Jaipur'),
    ('Nikhil Kulkarni', '9811110015', 'Nikhil Kulkarni', 'Nagpur', 'Nagpur'),
    ('Sangeeta Joshi', '9811110016', 'Sangeeta Joshi', 'Surat', 'Surat'),
    ('Imran Khan', '9811110017', 'Imran Khan', 'Bhopal', 'Bhopal'),
    ('Lakshmi Priya', '9811110018', 'Lakshmi Priya', 'Coimbatore', 'Coimbatore'),
    ('Deepak Saini', '9811110019', 'Deepak Saini', 'Chandigarh', 'Chandigarh'),
    ('Neha Agrawal', '9811110020', 'Neha Agrawal', 'Agra', 'Agra'),
    ('Vivek Ranjan', '9811110021', 'Vivek Ranjan', 'Patna', 'Patna'),
    ('Shalini Menon', '9811110022', 'Shalini Menon', 'Thiruvananthapuram', 'Thiruvananthapuram'),
    ('Gaurav Bhatia', '9811110023', 'Gaurav Bhatia', 'Gurugram', 'Gurugram'),
    ('Rekha Pawar', '9811110024', 'Rekha Pawar', 'Nashik', 'Nashik'),
    ('Sanjay Bansal', '9811110025', 'Sanjay Bansal', 'Ludhiana', 'Ludhiana'),
    ('Anitha V', '9811110026', 'Anitha V', 'Madurai', 'Madurai'),
    ('Mohammed Rafi', '9811110027', 'Mohammed Rafi', 'Kolkata', 'Kolkata'),
    ('Swati Kale', '9811110028', 'Swati Kale', 'Aurangabad', 'Aurangabad'),
    ('Prakash Chandra', '9811110029', 'Prakash Chandra', 'Varanasi', 'Varanasi'),
    ('Farah Sheikh', '9811110030', 'Farah Sheikh', 'Ahmedabad', 'Ahmedabad'),
]


def seed_customers():
    customers = []
    for name, phone, email, town, district in CUSTOMERS:
        c = Customer(
            name=name, phone=phone,
            email=f'{email.lower().replace(" ", ".")}@gmail.com',
            town=town, district=district,
            created_at=rand_date(date.today() - timedelta(days=600), date.today() - timedelta(days=10)),
        )
        storage.add_customer(c)
        customers.append(c)
    return customers


# ==============================================================================
# PURCHASES, PAYMENTS, ITEMS, WARRANTY, GRN
# ==============================================================================
def seed_transactions(products, brands, vendors, customers, users):
    today = date.today()
    start = today - timedelta(days=360)
    methods = ['Cash', 'Bank Transfer', 'Cheque', 'UPI']
    notes_pool = [
        'Stock replenishment', 'Seasonal demand order', 'Monthly indents',
        'Festive season stocking', 'New model launch purchase',
        'Bulk order for retail', 'Replenishment after sale spike', '',
    ]
    grn_notes = ['In good condition', 'Minor packaging damage', 'All items inspected & accepted',
                 'Received with invoice', 'Quality checked on receipt']

    # Map each vendor to the products they typically supply (by category/brand).
    vendor_specialties = [
        (0, ['Fans', 'Air Coolers']),
        (1, ['Gas Stoves', 'Kitchen Chimneys']),
        (2, ['Mixer Grinders', 'Grinders']),
        (3, ['Kitchen Chimneys', 'Gas Stoves']),
        (4, ['Fans', 'Water Heaters']),
        (5, ['Water Heaters', 'Rice Cookers']),
        (6, ['Air Coolers', 'Fans']),
        (7, ['Refrigerators', 'Washing Machines']),
        (8, ['Washing Machines', 'LED Televisions']),
        (9, ['LED Televisions']),
        (10, ['Rice Cookers', 'Grinders']),
        (11, ['Mixer Grinders', 'Rice Cookers']),
    ]
    vendor_products = {}
    for v_idx, cats in vendor_specialties:
        vendor_products[v_idx] = [p for p in products if p.category.name in cats]

    purchases = []
    num_purchases = 95
    for _ in range(num_purchases):
        v_idx = random.randint(0, len(vendors) - 1)
        pool = vendor_products[v_idx] or products
        product = random.choice(pool)

        qty = random.choice([5, 6, 8, 10, 12, 15, 20, 24, 25, 30, 40])
        unit_price = round(product.purchase_price * random.uniform(0.95, 1.08), 2)
        total = round(qty * unit_price, 2)
        purchase_date = rand_date(start, today)
        created_at = datetime.combine(purchase_date, datetime.min.time()) + timedelta(hours=random.randint(9, 19))

        ptype = random.choices(['Wholesale', 'Retail'], weights=[0.7, 0.3])[0]
        customer_id = random.choice(customers).id if ptype == 'Retail' and random.random() < 0.6 else None
        user_id = random.choice(users).id

        status = random.choices(
            ['Approved', 'Delivered', 'Pending', 'Draft', 'Cancelled'],
            weights=[0.42, 0.28, 0.14, 0.08, 0.08])[0]

        purchase = Purchase(
            purchase_id=f'PUR-{uuid.uuid4().hex[:8].upper()}',
            vendor_id=vendors[v_idx].id,
            brand_name=product.brand.name if product.brand else '',
            model_name=product.model,
            quantity=qty,
            purchase_date=purchase_date,
            unit_price=unit_price,
            total_amount=total,
            created_at=created_at,
            customer_id=customer_id,
            user_id=user_id,
            purchase_type=ptype,
            subtotal=total,
            total=total,
            status=status,
        )
        storage.add_purchase(purchase)
        purchases.append(purchase)

        # Purchase line item
        storage.add_purchase_item(PurchaseItem(
            purchase_id=purchase.id,
            product_id=product.id,
            brand=product.brand.name if product.brand else '',
            model=product.model,
            capacity=product.capacity,
            qty=qty,
            price=unit_price,
            total=total,
        ))

        # Warranty for appliance purchases
        if product.warranty_months and random.random() < 0.7:
            duration = f'{product.warranty_months} months'
            end_date = purchase_date + timedelta(days=product.warranty_months * 30)
            storage.add_warranty(Warranty(
                purchase_id=purchase.id,
                applicable=True,
                duration=duration,
                start_date=purchase_date,
                end_date=end_date,
            ))

        # WhatsApp message for retail customer-linked purchases
        if customer_id and random.random() < 0.8:
            sent = created_at + timedelta(minutes=random.randint(5, 240))
            storage.add_whatsapp_message(WhatsAppMessage(
                purchase_id=purchase.id,
                message_id=f'wamid.{random.randint(10**14, 10**15)}',
                status='Sent',
                sent_at=sent,
            ))

        # GRN for a subset of purchases
        if random.random() < 0.6:
            is_partial = random.random() < 0.15
            received_qty = max(1, qty - random.randint(1, max(1, qty // 3))) if is_partial else qty
            note = random.choice(grn_notes)
            if is_partial:
                note = random.choice(['Partial delivery — balance pending', 'Short supply, rest on backorder'])
            storage.add_goods_received(GoodsReceived(
                grn_number=f'GRN-{uuid.uuid4().hex[:6].upper()}',
                purchase_id=purchase.id,
                received_date=purchase_date + timedelta(days=random.randint(0, 5)),
                received_qty=received_qty,
                condition_notes=note,
                received_by=random.choice(users).name,
                created_at=created_at + timedelta(days=1),
            ))

    # ---------------------------------------------------------------------------
    # Payments: leave some vendors with outstanding balances, some fully settled.
    # ---------------------------------------------------------------------------
    for v_idx, vendor in enumerate(vendors):
        vendor_purchases = [p for p in purchases if p.vendor_id == vendor.id]
        if not vendor_purchases:
            continue
        owed = sum(p.total_amount for p in vendor_purchases)

        if v_idx % 5 == 0:          # fully paid
            remaining = owed
        elif v_idx % 5 == 1:        # no payments at all
            remaining = 0.0
        else:                       # partially paid (~55-85%)
            remaining = owed * random.uniform(0.55, 0.85)

        paid_target = round(owed - remaining, 2)
        paid_so_far = 0.0
        while paid_so_far < paid_target - 1:
            chunk = min(random.choice([5000, 10000, 15000, 25000, 50000]),
                        round(paid_target - paid_so_far, 2))
            if chunk < 500:
                break
            paid_so_far += chunk
            pmt_date = rand_date(start, today)
            storage.add_payment(Payment(
                vendor_id=vendor.id,
                payment_date=pmt_date,
                payment_method=random.choice(methods),
                amount_paid=round(chunk, 2),
                reference_number=f'REF-{random.randint(100000, 999999)}',
                notes=random.choice(notes_pool) or 'Payment against invoices',
                created_at=datetime.combine(pmt_date, datetime.min.time()) + timedelta(hours=random.randint(10, 18)),
            ))

    return purchases


# ==============================================================================
# OFFERS & OFFER MESSAGES
# ==============================================================================
def seed_offers(products, customers):
    today = date.today()
    offers_data = [
        ('Monsoon Fan Fest', 'Flat 10% off on all Crompton & Usha fans this monsoon.',
         ['Fans'], -10, 20, True),
        ('Kitchen Upgrade Sale', 'Special pricing on gas stoves and mixer grinders.',
         ['Gas Stoves', 'Mixer Grinders'], -5, 25, True),
        ('Cooler Season Discount', 'Save big on air coolers before summer ends.',
         ['Air Coolers'], -20, -5, True),
        ('Winter Heating Deals', 'Geyser and water heater combo offers.',
         ['Water Heaters'], 30, 80, False),
        ('New Year Mega Sale', 'Big discounts across LED TVs and washing machines.',
         ['LED Televisions', 'Washing Machines'], 5, 45, True),
    ]

    offers = []
    for title, desc, cats, start_off, end_off, active in offers_data:
        cat_ids = {c.name for c in storage.categories}
        offer_products = [p for p in products if p.category.name in cats]
        if not offer_products:
            continue
        offer = Offer(
            title=title,
            description=desc,
            product_ids=[p.id for p in random.sample(offer_products, min(4, len(offer_products)))],
            start_date=today + timedelta(days=start_off),
            end_date=today + timedelta(days=end_off),
            active=active,
            image='',
            message=f'{title}: {desc}',
        )
        storage.add_offer(offer)
        offers.append(offer)

        for customer in random.sample(customers, random.randint(3, 8)):
            status = random.choices(['Sent', 'Delivered', 'Failed', 'Not Sent'], weights=[0.6, 0.25, 0.1, 0.05])[0]
            storage.add_offer_message(OfferMessage(
                offer_id=offer.id,
                customer_id=customer.id,
                status=status,
                sent_at=datetime.now() - timedelta(days=random.randint(0, 30)) if status != 'Not Sent' else None,
            ))


# ==============================================================================
# SETTINGS
# ==============================================================================
def seed_settings():
    defaults = {
        'store_name': 'VEMA Home Appliances Ltd',
        'store_phone': '+91 9876543210',
        'store_email': 'contact@vema.com',
        'store_address': '123 Commercial Plaza, Main Street, Hyderabad',
        'invoice_prefix': 'VEMA-INV-',
        'whatsapp_phone_id': '',
        'whatsapp_account_id': '',
        'whatsapp_access_token': '',
        'message_template': 'Dear {{customer}}, thank you for purchasing from {{store}}. Your {{product}} carries a {{warranty}} warranty. - {{store}}',
    }
    for key, value in defaults.items():
        storage.add_setting(StoreSetting(key=key, value=value))


# ==============================================================================
# MAIN
# ==============================================================================
def main():
    print(f'Database: {storage.database_path}')
    reset_database()
    print('All existing data cleared.\n')

    users = seed_users()
    products, brand_map = seed_catalog()
    vendors = seed_vendors()
    customers = seed_customers()
    purchases = seed_transactions(products, brand_map, vendors, customers, users)
    seed_offers(products, customers)
    seed_settings()

    print('Synthetic data seeded successfully!\n')
    print('Summary:')
    print(f'  Roles           : {len(storage.roles)}')
    print(f'  Users           : {len(storage.users)}')
    print(f'  Categories      : {len(storage.categories)}')
    print(f'  Brands          : {len(storage.brands)}')
    print(f'  Products        : {len(storage.products)}')
    print(f'  Vendors         : {len(storage.vendors)}')
    print(f'  Customers       : {len(storage.customers)}')
    print(f'  Purchases       : {len(storage.purchases)}')
    print(f'  Purchase Items  : {len(storage.purchase_items)}')
    print(f'  Payments        : {len(storage.payments)}')
    print(f'  Goods Received  : {len(storage.goods_received)}')
    print(f'  Warranties      : {len(storage.warranties)}')
    print(f'  WhatsApp Msgs   : {len(storage.whatsapp_messages)}')
    print(f'  Offers          : {len(storage.offers)}')
    print(f'  Offer Messages  : {len(storage.offer_messages)}')
    print(f'  Settings        : {len(storage.settings)}')
    print(f'\nLogin: admin@example.com / adminpass')


if __name__ == '__main__':
    main()
