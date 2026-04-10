from django.core.management.base import BaseCommand
from inventory.models import RFIDUser, Category, Product


class Command(BaseCommand):
    help = 'Seed database with sample data'

    def handle(self, *args, **kwargs):
        # Categories
        cats = {}
        for name in ['Safety', 'Tools', 'Equipment', 'Electronics', 'Supplies']:
            c, _ = Category.objects.get_or_create(name=name)
            cats[name] = c

        # RFID Users
        users = [
            ('Andi Pratama',   'RFID-A1B2', 'technician', 'Maintenance'),
            ('Sari Dewi',      'RFID-C3D4', 'supervisor',  'Operations'),
            ('Budi Santoso',   'RFID-E5F6', 'engineer',    'R&D'),
        ]
        for name, code, role, dept in users:
            RFIDUser.objects.get_or_create(
                rfid_code=code,
                defaults={'full_name': name, 'role': role, 'department': dept}
            )

        # Products
        products = [
            ('Safety Gloves',    cats['Safety'],      'Rack A-1', 24, 30, 'Heat-resistant gloves'),
            ('Screwdriver Set',  cats['Tools'],       'Rack B-2',  8, 20, '6-piece precision set'),
            ('Voltage Tester',   cats['Equipment'],   'Rack C-1',  3, 10, 'Non-contact AC detector'),
            ('USB Drive 64GB',   cats['Electronics'], 'Drawer D-3',15,25,'USB 3.0 flash drive'),
            ('Safety Helmet',    cats['Safety'],      'Rack A-3',  1, 12, 'ANSI-rated hard hat'),
            ('Zip Ties (100x)',  cats['Supplies'],    'Bin E-1',  50,100, 'Nylon cable ties'),
        ]
        for name, cat, loc, stock, max_stock, desc in products:
            Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': cat, 'location': loc,
                    'stock': stock, 'max_stock': max_stock,
                    'description': desc, 'reorder_threshold': int(max_stock * 0.2),
                }
            )
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))