"""
All API views — pure Django JsonResponse (no DRF).
"""
import json, os
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone

from api.models import User, Category, Product, Cart, CartItem, Order, OrderItem, Review, Coupon, Wishlist
from api.auth import generate_token, jwt_required, admin_required


# ────────────────────────────────────────────────────────────────────────────────
# HELPERS
# ────────────────────────────────────────────────────────────────────────────────

def json_body(request):
    """Parse JSON request body safely."""
    try:
        return json.loads(request.body)
    except Exception:
        return {}


def product_to_dict(p, request=None):
    image_url = ''
    if p.image:
        if request:
            image_url = request.build_absolute_uri(p.image.url)
        else:
            image_url = p.image.url
    return {
        'id': p.id,
        'name': p.name,
        'slug': p.slug,
        'description': p.description,
        'price': str(p.price),
        'discount_price': str(p.discount_price) if p.discount_price else None,
        'effective_price': str(p.effective_price),
        'image': image_url,
        'stock': p.stock,
        'weight': p.weight,
        'is_featured': p.is_featured,
        'rating': str(p.rating),
        'total_reviews': p.total_reviews,
        'category': {'id': p.category.id, 'name': p.category.name, 'slug': p.category.slug} if p.category else None,
    }


# ────────────────────────────────────────────────────────────────────────────────
# AUTH VIEWS
# ────────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def register(request):
    """POST /api/register/"""
    data = json_body(request)
    email = data.get('email', '').strip().lower()
    name = data.get('name', '').strip()
    password = data.get('password', '')
    phone = data.get('phone', '').strip()
    address = data.get('address', '').strip()
    gender = data.get('gender', '').strip()

    if not email or not name or not password:
        return JsonResponse({'error': 'All fields are required'}, status=400)
    if len(password) < 6:
        return JsonResponse({'error': 'Password must be at least 6 characters'}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Email already registered'}, status=400)

    user = User.objects.create_user(email=email, name=name, password=password)
    user.phone = phone
    user.address = address
    user.gender = gender
    user.save()
    Cart.objects.create(user=user)  # auto-create cart
    token = generate_token(user)

    return JsonResponse({
        'token': token,
        'user': {'id': user.id, 'name': user.name, 'email': user.email},
    }, status=201)


@csrf_exempt
@require_http_methods(['POST'])
def login(request):
    """POST /api/login/"""
    data = json_body(request)
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid credentials'}, status=401)

    if not user.check_password(password):
        return JsonResponse({'error': 'Invalid credentials'}, status=401)
    if not user.is_active:
        return JsonResponse({'error': 'Account is disabled'}, status=403)

    # Ensure cart exists
    Cart.objects.get_or_create(user=user)
    token = generate_token(user)

    return JsonResponse({
        'token': token,
        'user': {
            'id': user.id, 
            'name': user.name, 
            'email': user.email,
            'is_staff': user.is_staff
        },
    })

def admin_redirect(request):
    """Securely redirect to the Admin Portal, forwarding any session tokens."""
    # Forward all query parameters (like ?token=...) using Django's native method
    admin_url = 'https://russy-admin.netlify.app'
    
    # Forward all query parameters (like ?token=...) using Django's native method
    query_params = request.GET.urlencode()
    if query_params:
        admin_url += ('?' if '?' not in admin_url else '&') + query_params
        
    return redirect(admin_url)


@csrf_exempt
@jwt_required
def profile(request):
    """GET/PUT /api/profile/"""
    user = request.current_user
    if request.method == 'GET':
        return JsonResponse({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone,
            'address': user.address,
            'gender': user.gender,
        })
    elif request.method == 'PUT':
        data = json_body(request)
        user.name = data.get('name', user.name)
        user.phone = data.get('phone', user.phone)
        user.address = data.get('address', user.address)
        user.gender = data.get('gender', user.gender)
        user.save()
        return JsonResponse({'message': 'Profile updated'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ────────────────────────────────────────────────────────────────────────────────
# CATEGORY VIEWS
# ────────────────────────────────────────────────────────────────────────────────

def categories(request):
    """GET /api/categories/"""
    cats = Category.objects.all()
    data = [{'id': c.id, 'name': c.name, 'slug': c.slug, 'icon': c.icon} for c in cats]
    return JsonResponse({'categories': data})


@csrf_exempt
@jwt_required
def cancel_order(request, order_id):
    """POST /api/orders/<id>/cancel/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        order = Order.objects.prefetch_related('items__product').get(id=order_id, user=request.current_user)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

    if order.status in ['shipped', 'delivered']:
        return JsonResponse({'error': 'Order cannot be cancelled at this stage'}, status=400)
        
    if order.status == 'cancelled':
        return JsonResponse({'message': 'Order is already cancelled'})

    order.status = 'cancelled'
    order.save()

    # Restore stock
    for item in order.items.all():
        product = item.product
        product.stock += item.quantity
        product.save()

    return JsonResponse({'message': 'Order cancelled successfully', 'status': order.status})


@csrf_exempt
@admin_required
def add_category(request):
    """POST /api/admin/categories/add/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    data = json_body(request)
    name = data.get('name', '').strip()
    slug = data.get('slug', '').strip()
    icon = data.get('icon', '').strip()
    
    if not name or not slug:
        return JsonResponse({'error': 'Name and slug are required'}, status=400)
        
    if Category.objects.filter(slug=slug).exists():
        return JsonResponse({'error': 'Category with this slug already exists'}, status=400)
        
    try:
        cat = Category.objects.create(name=name, slug=slug, icon=icon)
        return JsonResponse({
            'message': 'Category added successfully', 
            'category': {'id': cat.id, 'name': cat.name, 'slug': cat.slug, 'icon': cat.icon}
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@admin_required
def update_category(request, category_id):
    """POST/PUT /api/admin/categories/update/<id>/"""
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        cat = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)

    data = json_body(request)
    if 'name' in data: 
        cat.name = data.get('name').strip()
    if 'slug' in data:
        slug = data.get('slug').strip()
        if slug != cat.slug and Category.objects.filter(slug=slug).exists():
            return JsonResponse({'error': 'Category with this slug already exists'}, status=400)
        cat.slug = slug
    if 'icon' in data: 
        cat.icon = data.get('icon').strip()
        
    try:
        cat.save()
        return JsonResponse({
            'message': 'Category updated successfully', 
            'category': {'id': cat.id, 'name': cat.name, 'slug': cat.slug, 'icon': cat.icon}
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@admin_required
def delete_category(request, category_id):
    """DELETE /api/admin/categories/delete/<id>/"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        cat = Category.objects.get(id=category_id)
        cat.delete()
        return JsonResponse({'message': 'Category deleted successfully'})
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)


# ────────────────────────────────────────────────────────────────────────────────
# PRODUCT VIEWS
# ────────────────────────────────────────────────────────────────────────────────

def products(request):
    """GET /api/products/  — supports ?search=, ?category=, ?featured=, ?page="""
    qs = Product.objects.select_related('category').filter(stock__gt=0)

    search = request.GET.get('search', '')
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

    category_slug = request.GET.get('category', '')
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    if request.GET.get('featured') == 'true':
        qs = qs.filter(is_featured=True)

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        qs = qs.filter(price__gte=min_price)
    if max_price:
        qs = qs.filter(price__lte=max_price)

    paginator = Paginator(qs, 12)
    page_num = request.GET.get('page', 1)
    page = paginator.get_page(page_num)

    return JsonResponse({
        'products': [product_to_dict(p, request) for p in page],
        'total': paginator.count,
        'pages': paginator.num_pages,
        'current_page': page.number,
    })


def product_detail(request, slug):
    """GET /api/products/<slug>/"""
    try:
        p = Product.objects.select_related('category').get(slug=slug)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

    # Include reviews
    reviews = [
        {
            'id': r.id,
            'user': r.user.name,
            'rating': r.rating,
            'comment': r.comment,
            'created_at': r.created_at.isoformat(),
        }
        for r in p.reviews.select_related('user').order_by('-created_at')[:10]
    ]
    data = product_to_dict(p, request)
    data['reviews'] = reviews
    return JsonResponse(data)


@csrf_exempt
@jwt_required
def add_review(request, slug):
    """POST /api/products/<slug>/review/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        product = Product.objects.get(slug=slug)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

    data = json_body(request)
    rating = int(data.get('rating', 5))
    comment = data.get('comment', '').strip()

    if not comment:
        return JsonResponse({'error': 'Comment is required'}, status=400)
    if rating < 1 or rating > 5:
        return JsonResponse({'error': 'Rating must be 1-5'}, status=400)

    Review.objects.create(product=product, user=request.current_user, rating=rating, comment=comment)
    # Update product aggregate rating
    reviews = product.reviews.all()
    product.rating = sum(r.rating for r in reviews) / reviews.count()
    product.total_reviews = reviews.count()
    product.save()

    return JsonResponse({'message': 'Review added'}, status=201)


@admin_required
def admin_products(request):
    """GET /api/admin/products/ — Get all products including out of stock"""
    qs = Product.objects.select_related('category').all().order_by('-created_at')
    
    paginator = Paginator(qs, 20)
    page_num = request.GET.get('page', 1)
    page = paginator.get_page(page_num)

    return JsonResponse({
        'products': [product_to_dict(p, request) for p in page],
        'total': paginator.count,
        'pages': paginator.num_pages,
        'current_page': page.number,
    })


@csrf_exempt
@admin_required
def add_product(request):
    """POST /api/admin/products/add/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Handle multipart/form-data
    data = request.POST
    
    name = data.get('name', '').strip()
    slug = data.get('slug', '').strip()
    category_id = data.get('category_id')
    description = data.get('description', '').strip()
    price = data.get('price')
    discount_price = data.get('discount_price')
    stock = data.get('stock', 0)
    weight = data.get('weight', '100g')
    is_featured = data.get('is_featured') == 'true'
    image = request.FILES.get('image')

    if not name or not slug or not price:
        return JsonResponse({'error': 'Name, slug, and price are required'}, status=400)
        
    if Product.objects.filter(slug=slug).exists():
        return JsonResponse({'error': 'Product with this slug already exists'}, status=400)

    category = None
    if category_id:
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({'error': 'Category not found'}, status=400)

    try:
        product = Product.objects.create(
            name=name,
            slug=slug,
            category=category,
            description=description,
            price=price,
            discount_price=discount_price if discount_price else None,
            stock=stock,
            weight=weight,
            is_featured=is_featured,
            image=image
        )
        return JsonResponse({'message': 'Product added successfully', 'product': product_to_dict(product, request)}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@admin_required
def update_product(request, product_id):
    """POST /api/admin/products/update/<id>/"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

    data = request.POST
    
    if 'name' in data: product.name = data.get('name').strip()
    if 'slug' in data: 
        slug = data.get('slug').strip()
        if slug != product.slug and Product.objects.filter(slug=slug).exists():
            return JsonResponse({'error': 'Product with this slug already exists'}, status=400)
        product.slug = slug
        
    if 'category_id' in data:
        try:
            product.category = Category.objects.get(id=data.get('category_id'))
        except Category.DoesNotExist:
             return JsonResponse({'error': 'Category not found'}, status=400)
             
    if 'description' in data: product.description = data.get('description').strip()
    if 'price' in data: product.price = data.get('price')
    if 'discount_price' in data: 
        dp = data.get('discount_price')
        product.discount_price = dp if dp else None
    if 'stock' in data: product.stock = data.get('stock')
    if 'weight' in data: product.weight = data.get('weight')
    if 'is_featured' in data: product.is_featured = data.get('is_featured') == 'true'
    
    if 'image' in request.FILES:
        product.image = request.FILES.get('image')

    try:
        product.save()
        return JsonResponse({'message': 'Product updated successfully', 'product': product_to_dict(product, request)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@admin_required
def delete_product(request, product_id):
    """DELETE /api/admin/products/delete/<id>/"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        product = Product.objects.get(id=product_id)
        product.delete()
        return JsonResponse({'message': 'Product deleted successfully'})
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
        

# ────────────────────────────────────────────────────────────────────────────────
# CART VIEWS
# ────────────────────────────────────────────────────────────────────────────────

def cart_to_dict(cart):
    items = []
    total = 0
    for item in cart.items.select_related('product'):
        subtotal = item.subtotal
        total += subtotal
        items.append({
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.name,
            'product_slug': item.product.slug,
            'price': str(item.product.effective_price),
            'quantity': item.quantity,
            'subtotal': str(round(subtotal, 2)),
            'image': item.product.image.url if item.product.image else '',
        })
    return {'items': items, 'total': str(round(total, 2)), 'count': cart.items.count()}


@jwt_required
def cart(request):
    """GET /api/cart/"""
    cart_obj, _ = Cart.objects.get_or_create(user=request.current_user)
    return JsonResponse(cart_to_dict(cart_obj))


@csrf_exempt
@jwt_required
def cart_add(request):
    """POST /api/cart/add/  {product_id, quantity}"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = json_body(request)
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)

    if quantity < 1:
        return JsonResponse({'error': 'Quantity must be at least 1'}, status=400)
    if product.stock < quantity:
        return JsonResponse({'error': 'Insufficient stock'}, status=400)

    cart_obj, _ = Cart.objects.get_or_create(user=request.current_user)
    item, created = CartItem.objects.get_or_create(cart=cart_obj, product=product)
    if not created:
        item.quantity += quantity
    else:
        item.quantity = quantity
    item.save()

    return JsonResponse({'message': 'Added to cart', 'cart': cart_to_dict(cart_obj)})


@csrf_exempt
@jwt_required
def cart_update(request, item_id):
    """PUT /api/cart/update/<item_id>/  {quantity}   — quantity=0 removes item"""
    if request.method not in ['PUT', 'DELETE']:
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    cart_obj, _ = Cart.objects.get_or_create(user=request.current_user)
    try:
        item = CartItem.objects.get(id=item_id, cart=cart_obj)
    except CartItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)

    if request.method == 'DELETE':
        item.delete()
    else:
        data = json_body(request)
        quantity = int(data.get('quantity', 1))
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()

    return JsonResponse({'message': 'Cart updated', 'cart': cart_to_dict(cart_obj)})


@csrf_exempt
@jwt_required
def cart_clear(request):
    """DELETE /api/cart/clear/"""
    cart_obj, _ = Cart.objects.get_or_create(user=request.current_user)
    cart_obj.items.all().delete()
    return JsonResponse({'message': 'Cart cleared'})


# ────────────────────────────────────────────────────────────────────────────────
# ORDER VIEWS
# ────────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@jwt_required
def orders(request):
    """GET /api/orders/ — list user orders | POST — place new order"""
    user = request.current_user

    if request.method == 'GET':
        order_list = Order.objects.filter(user=user).prefetch_related('items__product').order_by('-created_at')
        result = []
        for o in order_list:
            result.append({
                'id': o.id,
                'status': o.status,
                'total_amount': str(o.total_amount),
                'shipping_address': o.shipping_address,
                'coupon_code': o.coupon_code,
                'discount_applied': str(o.discount_applied),
                'payment_method': o.payment_method,
                'payment_id': o.payment_id,
                'created_at': o.created_at.isoformat(),
                'items': [
                    {
                        'product_name': i.product.name,
                        'quantity': i.quantity,
                        'price': str(i.price),
                    }
                    for i in o.items.select_related('product')
                ],
            })
        return JsonResponse({'orders': result})

    elif request.method == 'POST':
        data = json_body(request)
        shipping_address = data.get('shipping_address', '').strip()
        payment_method = data.get('payment_method', 'cod')
        payment_id = data.get('payment_id', '')
        coupon_code = data.get('coupon_code', '').strip().upper()

        if not shipping_address:
            return JsonResponse({'error': 'Shipping address is required'}, status=400)

        cart_obj, _ = Cart.objects.get_or_create(user=user)
        if not cart_obj.items.exists():
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        total = float(sum(item.subtotal for item in cart_obj.items.select_related('product')))
        discount = 0

        # Validate coupon
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if coupon.used_count < coupon.max_uses:
                    if not coupon.expiry or coupon.expiry >= timezone.now().date():
                        discount = round(total * coupon.discount_percent / 100, 2)
                        coupon.used_count += 1
                        coupon.save()
            except Coupon.DoesNotExist:
                pass  # invalid coupon — just ignore

        final_total = max(0, total - discount)

        order = Order.objects.create(
            user=user,
            total_amount=final_total,
            shipping_address=shipping_address,
            payment_method=payment_method,
            payment_id=payment_id,
            coupon_code=coupon_code,
            discount_applied=discount,
        )

        for item in cart_obj.items.select_related('product'):
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.effective_price,
                cost_price=item.product.cost_price,
            )
            # Reduce stock
            item.product.stock = max(0, item.product.stock - item.quantity)
            item.product.save()

        cart_obj.items.all().delete()  # Clear cart after order

        return JsonResponse({
            'message': 'Order placed successfully',
            'order_id': order.id,
            'total_amount': str(final_total),
            'discount_applied': str(discount),
        }, status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@jwt_required
def order_detail(request, order_id):
    """GET /api/orders/<order_id>/"""
    try:
        order = Order.objects.prefetch_related('items__product').get(id=order_id, user=request.current_user)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

    return JsonResponse({
        'id': order.id,
        'status': order.status,
        'total_amount': str(order.total_amount),
        'shipping_address': order.shipping_address,
        'coupon_code': order.coupon_code,
        'discount_applied': str(order.discount_applied),
        'payment_method': order.payment_method,
        'payment_id': order.payment_id,
        'created_at': order.created_at.isoformat(),
        'items': [
            {
                'product_name': i.product.name,
                'product_slug': i.product.slug,
                'quantity': i.quantity,
                'price': str(i.price),
                'image': i.product.image.url if i.product.image else '',
            }
            for i in order.items.select_related('product')
        ],
    })


# ────────────────────────────────────────────────────────────────────────────────
# WISHLIST VIEWS
# ────────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@jwt_required
def wishlist(request):
    """GET /api/wishlist/ | POST {product_id} to add | DELETE to remove"""
    user = request.current_user

    if request.method == 'GET':
        items = Wishlist.objects.filter(user=user).select_related('product__category')
        return JsonResponse({
            'wishlist': [
                {
                    'id': w.id,
                    'product': product_to_dict(w.product, request),
                }
                for w in items
            ]
        })

    elif request.method == 'POST':
        data = json_body(request)
        product_id = data.get('product_id')
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'error': 'Product not found'}, status=404)

        obj, created = Wishlist.objects.get_or_create(user=user, product=product)
        msg = 'Added to wishlist' if created else 'Already in wishlist'
        return JsonResponse({'message': msg}, status=201 if created else 200)

    elif request.method == 'DELETE':
        data = json_body(request)
        product_id = data.get('product_id')
        Wishlist.objects.filter(user=user, product_id=product_id).delete()
        return JsonResponse({'message': 'Removed from wishlist'})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ────────────────────────────────────────────────────────────────────────────────
# COUPON VALIDATION
# ────────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@jwt_required
def validate_coupon(request):
    """POST /api/validate-coupon/  {coupon_code, total}"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = json_body(request)
    code = data.get('coupon_code', '').strip().upper()
    total = float(data.get('total', 0))

    try:
        coupon = Coupon.objects.get(code=code, is_active=True)
    except Coupon.DoesNotExist:
        return JsonResponse({'error': 'Invalid coupon code'}, status=400)

    if coupon.used_count >= coupon.max_uses:
        return JsonResponse({'error': 'Coupon usage limit reached'}, status=400)
    if coupon.expiry and coupon.expiry < timezone.now().date():
        return JsonResponse({'error': 'Coupon has expired'}, status=400)

    discount = round(total * coupon.discount_percent / 100, 2)
    return JsonResponse({
        'valid': True,
        'discount_percent': coupon.discount_percent,
        'discount_amount': str(discount),
        'final_total': str(round(max(0, total - discount), 2)),
    })


# ────────────────────────────────────────────────────────────────────────────────
# ADMIN ORDERS
# ────────────────────────────────────────────────────────────────────────────────

@admin_required
def admin_orders(request):
    """GET /api/admin/orders/ — List all orders for admin dashboard"""
    qs = Order.objects.select_related('user').prefetch_related('items__product').all().order_by('-created_at')
    
    paginator = Paginator(qs, 20)
    page_num = request.GET.get('page', 1)
    page = paginator.get_page(page_num)

    result = []
    for o in page:
        result.append({
            'id': o.id,
            'user': o.user.email,
            'user_name': o.user.name,
            'status': o.status,
            'total_amount': str(o.total_amount),
            'shipping_address': o.shipping_address,
            'coupon_code': o.coupon_code,
            'discount_applied': str(o.discount_applied),
            'payment_id': o.payment_id,
            'created_at': o.created_at.isoformat(),
            'items': [
                {
                    'product_name': i.product.name,
                    'quantity': i.quantity,
                    'price': str(i.price),
                }
                for i in o.items.select_related('product')
            ],
        })

    return JsonResponse({
        'orders': result,
        'total': paginator.count,
        'pages': paginator.num_pages,
        'current_page': page.number,
    })


@admin_required
def admin_stats(request):
    """GET /api/admin/stats/ — Live dashboard statistics"""

    total_orders = Order.objects.exclude(status='cancelled').count()
    total_products = Product.objects.count()
    total_customers = Order.objects.exclude(status='cancelled').values('user').distinct().count()
    orders_revenue = Order.objects.exclude(status='cancelled').aggregate(total=Sum('total_amount'))['total'] or 0
    total_revenue = float(orders_revenue)

    # Recent orders (last 5)
    recent_orders_qs = Order.objects.select_related('user').prefetch_related('items__product').order_by('-created_at')[:5]
    recent_orders = []
    for o in recent_orders_qs:
        recent_orders.append({
            'id': o.id,
            'user': o.user.name,
            'email': o.user.email,
            'status': o.status,
            'total_amount': str(o.total_amount),
            'created_at': o.created_at.isoformat(),
            'items_count': o.items.count(),
        })

    # Low stock products (stock < 10)
    low_stock_qs = Product.objects.filter(stock__lt=10).order_by('stock')[:5]
    low_stock = [{'id': p.id, 'name': p.name, 'stock': p.stock} for p in low_stock_qs]

    # Monthly revenue breakdown (last 6 months)
    from django.db.models.functions import TruncMonth
    from datetime import timedelta
    six_months_ago = timezone.now() - timedelta(days=180)
    monthly_data = (
        Order.objects
        .filter(created_at__gte=six_months_ago)
        .exclude(status='cancelled')
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(revenue=Sum('total_amount'), count=Count('id'))
        .order_by('month')
    )
    monthly_chart = [
        {
            'month': entry['month'].strftime('%b %Y'),
            'revenue': float(entry['revenue'] or 0),
            'orders': entry['count'],
        }
        for entry in monthly_data
    ]

    # Top Selling Products (Top 5 by quantity)
    from django.db.models import Sum as SumQty
    top_products_qs = (
        OrderItem.objects
        .exclude(order__status='cancelled')
        .values('product__id', 'product__name')
        .annotate(total_sold=SumQty('quantity'))
        .order_by('-total_sold')[:5]
    )
    top_products = [
        {'id': p['product__id'], 'name': p['product__name'], 'sold': p['total_sold']}
        for p in top_products_qs
    ]

    return JsonResponse({
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_products': total_products,
        'total_customers': total_customers,
        'recent_orders': recent_orders,
        'low_stock': low_stock,
        'monthly_chart': monthly_chart,
        'top_products': top_products,
    })


@csrf_exempt
@admin_required
@require_http_methods(['POST', 'PUT'])
def update_order_status(request, order_id):
    """POST /api/admin/orders/<id>/status/"""
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'}, status=404)

    data = json_body(request)
    status = data.get('status')
    
    valid_statuses = [c[0] for c in Order.STATUS_CHOICES]
    if status not in valid_statuses:
        return JsonResponse({'error': f'Invalid status. Must be one of {valid_statuses}'}, status=400)

    order.status = status
    order.save()
    
    return JsonResponse({'message': 'Order status updated successfully', 'status': order.status})


# ────────────────────────────────────────────────────────────────────────────────
# ADMIN EXTENSIONS
# ────────────────────────────────────────────────────────────────────────────────

@admin_required
def admin_payments(request):
    """GET /api/admin/payments/ — Detailed Profit & Loss Analytics"""
    # Orders exclude cancelled
    valid_orders = Order.objects.exclude(status='cancelled').prefetch_related('items')
    
    total_revenue = 0
    total_cogs = 0 # Cost of Goods Sold
    
    for order in valid_orders:
        for item in order.items.all():
            total_revenue += float(item.price * item.quantity)
            total_cogs += float(item.cost_price * item.quantity)
    
    net_profit = total_revenue - total_cogs
    margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Simple Monthly Breakdown
    from django.db.models.functions import TruncMonth
    from django.db.models import Sum, F
    from datetime import timedelta
    six_months_ago = timezone.now() - timedelta(days=180)
    
    monthly_data = (
        OrderItem.objects
        .filter(order__created_at__gte=six_months_ago)
        .exclude(order__status='cancelled')
        .annotate(month=TruncMonth('order__created_at'))
        .values('month')
        .annotate(
            revenue=Sum(F('price') * F('quantity')),
            cost=Sum(F('cost_price') * F('quantity'))
        )
        .order_by('month')
    )
    
    chart_data = []
    for entry in monthly_data:
        chart_data.append({
            'month': entry['month'].strftime('%b %Y'),
            'revenue': float(entry['revenue'] or 0),
            'cost': float(entry['cost'] or 0),
            'profit': float(entry['revenue'] or 0) - float(entry['cost'] or 0)
        })

    # Recent High-Value Orders
    high_value_orders = Order.objects.exclude(status='cancelled').select_related('user').order_by('-total_amount')[:10]
    high_value_list = [{
        'id': o.id,
        'user': o.user.name,
        'amount': str(o.total_amount),
        'method': o.payment_method,
        'status': o.status,
        'date': o.created_at.isoformat()
    } for o in high_value_orders]

    return JsonResponse({
        'overview': {
            'revenue': total_revenue,
            'cost': total_cogs,
            'profit': net_profit,
            'margin': round(margin, 2)
        },
        'chart': chart_data,
        'recent_transactions': high_value_list
    })

@admin_required
def admin_info(request):
    """GET /api/admin/info/ — System Telemetry"""
    import sys
    import platform
    import django
    
    database_size = "SQLite Local"
    active_users = User.objects.count()
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    
    return JsonResponse({
        'system': {
            'os': platform.system() + ' ' + platform.release(),
            'python_version': sys.version.split(' ')[0],
            'django_version': django.get_version(),
            'database': 'SQLite3'
        },
        'metrics': {
            'total_users': active_users,
            'total_products': total_products,
            'total_orders': total_orders,
        },
        'status': 'Healthy 🟢'
    })
