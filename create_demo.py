from dotenv import load_dotenv

load_dotenv()

from app.storage import storage
from app.models import Role, User, Category, Brand, Product, Customer

# Ensure current storage data is loaded.
storage.ensure_data()

# Roles
admin_role = storage.find_role_by_name('Admin')
if not admin_role:
    admin_role = storage.add_role(Role(name='Admin'))
staff_role = storage.find_role_by_name('Staff')
if not staff_role:
    staff_role = storage.add_role(Role(name='Staff'))

# Admin user
if not storage.find_user_by_email('admin@example.com'):
    user = User(name='Administrator', email='admin@example.com', phone='0000000000', role_id=admin_role.id)
    user.set_password('adminpass')
    storage.add_user(user)

# Categories & Brands
categories = ['Fans', 'Mixi', 'Grinder', 'Gas Stove', 'Coolers', 'Geysers']
for name in categories:
    if not storage.find_category_by_name(name):
        storage.add_category(Category(name=name))

brands = ['Preethi', 'Ganga', 'Crompton', 'Usha', 'Panasonic', 'Lakshmi']
for name in brands:
    if not any(b.name == name for b in storage.brands):
        storage.add_brand(Brand(name=name))

# Sample products
if not storage.products:
    fan_cat = next((c for c in storage.categories if c.name == 'Fans'), None)
    brand = next((b for b in storage.brands if b.name == 'Crompton'), None)
    if fan_cat and brand:
        product = Product(name='Crompton Fan 1200mm', category_id=fan_cat.id, brand_id=brand.id,
                          model='CF-1200', capacity='1200mm', selling_price=2500, stock=25, warranty_months=24)
        storage.add_product(product)

# Sample customer
if not storage.find_customer_by_phone('9998887776'):
    customer = Customer(name='Demo Customer', phone='9998887776', email='demo@example.com', town='DemoTown', district='DemoDist')
    storage.add_customer(customer)

print('Demo data created. Admin: admin@example.com / adminpass')
