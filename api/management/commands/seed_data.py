"""
Management command to seed the database with sample Russy Masala products.
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from api.models import Category, Product, Coupon, User


class Command(BaseCommand):
    help = 'Seeds the database with sample Russy Masala data'

    def handle(self, *args, **options):
        self.stdout.write('🌶️  Seeding Russy Masala database...')

        # ── Categories ──────────────────────────────────────────────────────
        cats = [
            {'name': 'Whole Spices', 'slug': 'whole-spices', 'icon': '🌿'},
            {'name': 'Ground Spices', 'slug': 'ground-spices', 'icon': '🥄'},
            {'name': 'Blended Masalas', 'slug': 'blended-masalas', 'icon': '🫙'},
            {'name': 'Seeds & Grains', 'slug': 'seeds-grains', 'icon': '🌾'},
            {'name': 'Exotic & Rare', 'slug': 'exotic-rare', 'icon': '✨'},
        ]
        category_map = {}
        for c in cats:
            obj, _ = Category.objects.get_or_create(slug=c['slug'], defaults={'name': c['name'], 'icon': c['icon']})
            category_map[c['slug']] = obj

        # ── Products ──────────────────────────────────────────────────────
        products = [
            {'name': 'Russy Garam Masala', 'slug': 'russy-garam-masala', 'category': 'blended-masalas', 'price': 120, 'discount_price': 99, 'weight': '100g', 'stock': 150, 'is_featured': True, 'rating': 4.8, 'description': 'Our signature premium Garam Masala blend crafted from 18 authentic spices. Perfect for curries, biryanis, and gravies.'},
            {'name': 'Turmeric Powder', 'slug': 'turmeric-powder', 'category': 'ground-spices', 'price': 80, 'discount_price': None, 'weight': '200g', 'stock': 200, 'is_featured': True, 'rating': 4.7, 'description': 'Pure, high-curcumin turmeric sourced from the farms of Erode. Bright yellow colour and earthy aroma.'},
            {'name': 'Red Chilli Powder', 'slug': 'red-chilli-powder', 'category': 'ground-spices', 'price': 90, 'discount_price': 75, 'weight': '200g', 'stock': 180, 'is_featured': True, 'rating': 4.6, 'description': 'Fiery Kashmiri red chilli blended with Guntur variety for deep colour and balanced heat.'},
            {'name': 'Coriander Powder', 'slug': 'coriander-powder', 'category': 'ground-spices', 'price': 70, 'discount_price': None, 'weight': '200g', 'stock': 170, 'is_featured': False, 'rating': 4.5, 'description': 'Freshly ground dhania with a citrusy warmth. Stone-ground to retain volatile oils and aroma.'},
            {'name': 'Cumin Seeds', 'slug': 'cumin-seeds', 'category': 'seeds-grains', 'price': 110, 'discount_price': 95, 'weight': '100g', 'stock': 140, 'is_featured': False, 'rating': 4.7, 'description': 'Bold, earthy rajasthani jeera with intense nutty flavour. Essential for tadkas and biryanis.'},
            {'name': 'Cardamom (Elaichi)', 'slug': 'cardamom-elaichi', 'category': 'whole-spices', 'price': 350, 'discount_price': 299, 'weight': '50g', 'stock': 80, 'is_featured': True, 'rating': 4.9, 'description': 'Premium green cardamom from Kerala — plump pods bursting with sweet, floral perfume.'},
            {'name': 'Cloves (Laung)', 'slug': 'cloves-laung', 'category': 'whole-spices', 'price': 280, 'discount_price': None, 'weight': '50g', 'stock': 90, 'is_featured': False, 'rating': 4.6, 'description': 'Hand-picked, sun-dried cloves with a warm, pungent bite. Used in rice dishes, masalas and chai.'},
            {'name': 'Chicken Masala', 'slug': 'chicken-masala', 'category': 'blended-masalas', 'price': 130, 'discount_price': 110, 'weight': '100g', 'stock': 160, 'is_featured': True, 'rating': 4.8, 'description': 'Restaurant-style chicken masala blend with just the right heat and smokiness. Guaranteed finger-licking results.'},
            {'name': 'Biryani Masala', 'slug': 'biryani-masala', 'category': 'blended-masalas', 'price': 140, 'discount_price': 120, 'weight': '100g', 'stock': 120, 'is_featured': True, 'rating': 4.9, 'description': 'Aromatic biryani masala with saffron notes. Transforms every pot into a royal dum experience.'},
            {'name': 'Saffron (Kesar)', 'slug': 'saffron-kesar', 'category': 'exotic-rare', 'price': 599, 'discount_price': 549, 'weight': '1g', 'stock': 50, 'is_featured': True, 'rating': 4.9, 'description': 'Kashmiri Grade-A saffron threads — deep crimson with honey and floral notes. A true luxury spice.'},
            {'name': 'Mustard Seeds', 'slug': 'mustard-seeds', 'category': 'seeds-grains', 'price': 60, 'discount_price': None, 'weight': '200g', 'stock': 220, 'is_featured': False, 'rating': 4.4, 'description': 'Big, bold black mustard seeds for South Indian tadkas and pickles.'},
            {'name': 'Sambhar Masala', 'slug': 'sambhar-masala', 'category': 'blended-masalas', 'price': 115, 'discount_price': 99, 'weight': '100g', 'stock': 130, 'is_featured': False, 'rating': 4.7, 'description': 'Authentic South Indian sambhar masala — tangy, spicy and perfectly balanced.'},
        ]

        for p in products:
            Product.objects.get_or_create(
                slug=p['slug'],
                defaults={
                    'name': p['name'],
                    'category': category_map[p['category']],
                    'price': p['price'],
                    'discount_price': p['discount_price'],
                    'weight': p['weight'],
                    'stock': p['stock'],
                    'is_featured': p['is_featured'],
                    'rating': p['rating'],
                    'total_reviews': 0,
                    'description': p['description'],
                }
            )

        # ── Coupons ──────────────────────────────────────────────────────
        coupons = [
            {'code': 'RUSSY10', 'discount_percent': 10, 'max_uses': 500},
            {'code': 'SPICE20', 'discount_percent': 20, 'max_uses': 100},
            {'code': 'WELCOME15', 'discount_percent': 15, 'max_uses': 1000},
        ]
        for c in coupons:
            Coupon.objects.get_or_create(code=c['code'], defaults={'discount_percent': c['discount_percent'], 'max_uses': c['max_uses']})

        # ── Superuser ──────────────────────────────────────────────────────
        if not User.objects.filter(email='admin@russy.com').exists():
            User.objects.create_superuser(email='admin@russy.com', name='Admin', password='admin123')
            self.stdout.write('  ✅ Superuser created — admin@russy.com / admin123')

        self.stdout.write(self.style.SUCCESS('✅ Seed complete! 12 products, 3 coupons added.'))
