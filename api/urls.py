from django.urls import path
from api import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('profile/', views.profile, name='profile'),

    # ── Categories ────────────────────────────────
    path('categories/', views.categories, name='categories'),

    # ── Products ──────────────────────────────────
    path('products/', views.products, name='products'),
    path('products/<slug:slug>/', views.product_detail, name='product-detail'),
    path('products/<slug:slug>/review/', views.add_review, name='add-review'),

    # ── Cart ──────────────────────────────────────
    path('cart/', views.cart, name='cart'),
    path('cart/add/', views.cart_add, name='cart-add'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart-update'),
    path('cart/clear/', views.cart_clear, name='cart-clear'),

    # ── Orders ────────────────────────────────────
    path('orders/', views.orders, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order-detail'),

    # ── Wishlist ──────────────────────────────────
    path('wishlist/', views.wishlist, name='wishlist'),

    # ── Coupons ───────────────────────────────────
    path('validate-coupon/', views.validate_coupon, name='validate-coupon'),
    
    # ── Admin Routes ──────────────────────────────
    path('admin/categories/add/', views.add_category, name='admin-add-category'),
    path('admin/categories/update/<int:category_id>/', views.update_category, name='admin-update-category'),
    path('admin/categories/delete/<int:category_id>/', views.delete_category, name='admin-delete-category'),
    path('admin/products/', views.admin_products, name='admin-products'),
    path('admin/products/add/', views.add_product, name='admin-add-product'),
    path('admin/products/update/<int:product_id>/', views.update_product, name='admin-update-product'),
    path('admin/products/delete/<int:product_id>/', views.delete_product, name='admin-delete-product'),
    path('admin/orders/', views.admin_orders, name='admin-orders'),
    path('admin/orders/<int:order_id>/status/', views.update_order_status, name='admin-update-order-status'),
    path('admin/stats/', views.admin_stats, name='admin-stats'),
]
