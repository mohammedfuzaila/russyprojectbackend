from django.contrib import admin
from api.models import User, Category, Product, Cart, CartItem, Order, OrderItem, Review, Coupon, Wishlist


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'phone', 'is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'name']
    list_filter = ['is_active', 'is_staff']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon']
    prepopulated_fields = {'slug': ('name',)}


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'discount_price', 'stock', 'is_featured', 'rating']
    list_filter = ['category', 'is_featured']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['stock', 'is_featured', 'discount_price']

admin.site.register(Product, ProductAdmin)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'total_amount', 'payment_id', 'created_at']
    list_filter = ['status']
    search_fields = ['user__email', 'payment_id']
    list_editable = ['status']
    inlines = [OrderItemInline]
    readonly_fields = ['user', 'total_amount', 'payment_id', 'coupon_code', 'discount_applied', 'created_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at']
    list_filter = ['rating']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percent', 'used_count', 'max_uses', 'is_active', 'expiry']
    list_editable = ['is_active']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']


# Admin site branding
admin.site.site_header = "Russy Masala Admin"
admin.site.site_title = "Russy Masala"
admin.site.index_title = "Manage Your Spice Store"
