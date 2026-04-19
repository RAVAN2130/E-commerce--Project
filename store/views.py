import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from .models import (
    Product, Customer, Sale, SaleItem, Supplier,
    PurchaseOrder, Category, Cart, CartItem,
    Order, OrderItem, SellerProfile, ProductReview
)
from .forms import (
    ProductForm, SellerProductForm, CustomerForm, SupplierForm,
    SaleForm, SaleItemFormSet, PurchaseOrderForm,
    PurchaseItemFormSet, SellerApplicationForm
)


# ── Role helpers ───────────────────────────────────────────────────────
def is_admin(user):
    return user.is_superuser


def is_salesperson(user):
    return user.is_superuser or user.groups.filter(name='Salesperson').exists()


def is_seller(user):
    return user.groups.filter(name='Seller').exists() or user.is_superuser


def is_buyer(user):
    return user.groups.filter(name='Buyer').exists()


def admin_required(view_func):
    return login_required(user_passes_test(is_admin, login_url='/login/')(view_func))


def salesperson_required(view_func):
    return login_required(user_passes_test(is_salesperson, login_url='/login/')(view_func))


def seller_required(view_func):
    return login_required(user_passes_test(is_seller, login_url='/login/')(view_func))


# ── Dashboard ──────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    if is_buyer(request.user) and not request.user.is_superuser:
        return redirect('buyer_dashboard')
    if is_seller(request.user) and not request.user.is_superuser:
        return redirect('seller_dashboard')

    today = timezone.now().date()
    month_start = today.replace(day=1)
    total_products = Product.objects.count()
    low_stock = Product.objects.filter(stock_qty__lte=F('reorder_level')).count()
    total_customers = Customer.objects.count()
    pending_sellers = SellerProfile.objects.filter(status='pending').count()

    if request.user.is_superuser:
        today_sales = Sale.objects.filter(sale_date__date=today, status='completed')
        monthly_sales = Sale.objects.filter(sale_date__date__gte=month_start, status='completed')
        recent_sales = Sale.objects.order_by('-sale_date')[:5]
        recent_orders = Order.objects.order_by('-created_at')[:5]
    else:
        today_sales = Sale.objects.filter(sale_date__date=today, status='completed', created_by=request.user)
        monthly_sales = Sale.objects.filter(sale_date__date__gte=month_start, status='completed', created_by=request.user)
        recent_sales = Sale.objects.filter(created_by=request.user).order_by('-sale_date')[:5]
        recent_orders = Order.objects.order_by('-created_at')[:5]

    today_revenue = sum(s.grand_total for s in today_sales)
    monthly_revenue = sum(s.grand_total for s in monthly_sales)
    low_stock_products = Product.objects.filter(stock_qty__lte=F('reorder_level'))[:5]

    context = {
        'total_products': total_products,
        'low_stock': low_stock,
        'total_customers': total_customers,
        'today_revenue': today_revenue,
        'monthly_revenue': monthly_revenue,
        'recent_sales': recent_sales,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'pending_sellers': pending_sellers,
    }
    return render(request, 'store/dashboard.html', context)


# ── Products ───────────────────────────────────────────────────────────
@login_required
def product_list(request):
    q = request.GET.get('q', '')
    products = Product.objects.select_related('category').order_by('name')
    if q:
        products = products.filter(name__icontains=q) | products.filter(sku__icontains=q)
    return render(request, 'store/product_list.html', {'products': products, 'q': q})


@admin_required
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Product added.')
        return redirect('product_list')
    return render(request, 'store/product_form.html', {'form': form, 'title': 'Add Product'})


@admin_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if form.is_valid():
        form.save()
        messages.success(request, 'Product updated.')
        return redirect('product_list')
    return render(request, 'store/product_form.html', {'form': form, 'title': 'Edit Product'})


@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted.')
        return redirect('product_list')
    return render(request, 'store/confirm_delete.html', {'object': product, 'type': 'Product'})


# ── Sales ──────────────────────────────────────────────────────────────
@salesperson_required
def sale_list(request):
    sales = Sale.objects.select_related('customer').order_by('-sale_date') if request.user.is_superuser else Sale.objects.filter(created_by=request.user).select_related('customer').order_by('-sale_date')
    return render(request, 'store/sale_list.html', {'sales': sales})


@salesperson_required
def sale_create(request):
    form = SaleForm(request.POST or None)
    formset = SaleItemFormSet(request.POST or None)
    if form.is_valid() and formset.is_valid():
        sale = form.save(commit=False)
        sale.created_by = request.user
        ts = timezone.now().strftime('%Y%m%d%H%M')
        sale.invoice_no = f'INV-{ts}-{random.randint(10,99)}'
        sale.save()
        for item in formset.save(commit=False):
            item.sale = sale
            item.product.stock_qty -= item.quantity
            item.product.save()
            item.save()
        messages.success(request, f'Sale {sale.invoice_no} recorded!')
        return redirect('sale_list')
    return render(request, 'store/sale_form.html', {'form': form, 'formset': formset})


@salesperson_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale, pk=pk) if request.user.is_superuser else get_object_or_404(Sale, pk=pk, created_by=request.user)
    return render(request, 'store/sale_detail.html', {'sale': sale})


# ── Customers ──────────────────────────────────────────────────────────
@salesperson_required
def customer_list(request):
    customers = Customer.objects.order_by('name')
    return render(request, 'store/customer_list.html', {'customers': customers})


@salesperson_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Customer added.')
        return redirect('customer_list')
    return render(request, 'store/generic_form.html', {'form': form, 'title': 'Add Customer'})


@salesperson_required
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if form.is_valid():
        form.save()
        messages.success(request, 'Customer updated.')
        return redirect('customer_list')
    return render(request, 'store/generic_form.html', {'form': form, 'title': 'Edit Customer'})


# ── Suppliers ──────────────────────────────────────────────────────────
@admin_required
def supplier_list(request):
    return render(request, 'store/supplier_list.html', {'suppliers': Supplier.objects.order_by('name')})


@admin_required
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Supplier added.')
        return redirect('supplier_list')
    return render(request, 'store/generic_form.html', {'form': form, 'title': 'Add Supplier'})


# ── Purchases ──────────────────────────────────────────────────────────
@admin_required
def purchase_list(request):
    return render(request, 'store/purchase_list.html', {'orders': PurchaseOrder.objects.select_related('supplier').order_by('-order_date')})


@admin_required
def purchase_create(request):
    form = PurchaseOrderForm(request.POST or None)
    formset = PurchaseItemFormSet(request.POST or None)
    if form.is_valid() and formset.is_valid():
        order = form.save(commit=False)
        order.ordered_by = request.user
        order.save()
        total = 0
        for item in formset.save(commit=False):
            item.order = order
            item.save()
            total += item.line_total
            if order.status == 'received':
                item.product.stock_qty += item.quantity
                item.product.save()
        order.total_amount = total
        order.save()
        messages.success(request, 'Purchase order created.')
        return redirect('purchase_list')
    return render(request, 'store/purchase_form.html', {'form': form, 'formset': formset})


# ── Reports ────────────────────────────────────────────────────────────
@admin_required
def reports(request):
    top_products = SaleItem.objects.values('product__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:5]
    monthly = []
    for i in range(5, -1, -1):
        d = timezone.now().date().replace(day=1) - timedelta(days=i * 30)
        m_sales = Sale.objects.filter(sale_date__year=d.year, sale_date__month=d.month, status='completed')
        revenue = sum(s.grand_total for s in m_sales)
        m_purchases = PurchaseOrder.objects.filter(order_date__year=d.year, order_date__month=d.month, status='received')
        cost = sum(p.total_amount for p in m_purchases)
        monthly.append({'month': d.strftime('%b %Y'), 'revenue': revenue, 'cost': cost, 'profit': revenue - cost})

    total_revenue = sum(m['revenue'] for m in monthly)
    total_cost = sum(m['cost'] for m in monthly)
    total_profit = total_revenue - total_cost
    profit_margin = round((total_profit / total_revenue * 100), 1) if total_revenue > 0 else 0

    top_customers = sorted([
        {'name': c.name, 'total_spent': sum(s.grand_total for s in Sale.objects.filter(customer=c, status='completed')), 'total_orders': Sale.objects.filter(customer=c).count()}
        for c in Customer.objects.all()
        if sum(s.grand_total for s in Sale.objects.filter(customer=c, status='completed')) > 0
    ], key=lambda x: x['total_spent'], reverse=True)[:5]

    total_online_orders = Order.objects.count()
    online_revenue = sum(o.grand_total for o in Order.objects.filter(status='delivered'))

    context = {
        'top_products': top_products, 'monthly': monthly,
        'total_revenue': total_revenue, 'total_cost': total_cost,
        'total_profit': total_profit, 'profit_margin': profit_margin,
        'top_customers': top_customers,
        'total_online_orders': total_online_orders,
        'online_revenue': online_revenue,
        'total_sellers': SellerProfile.objects.filter(status='approved').count(),
        'pending_sellers': SellerProfile.objects.filter(status='pending').count(),
    }
    return render(request, 'store/reports.html', context)


# ── Buyer Registration ─────────────────────────────────────────────────
def register(request):
    if request.user.is_authenticated:
        return redirect('buyer_dashboard')
    form = UserCreationForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        buyer_group, _ = Group.objects.get_or_create(name='Buyer')
        user.groups.add(buyer_group)
        login(request, user)
        messages.success(request, f'Welcome {user.username}!')
        return redirect('buyer_dashboard')
    return render(request, 'store/register.html', {'form': form})


# ── Public Shop ────────────────────────────────────────────────────────
def shop(request):
    q = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    products = Product.objects.filter(stock_qty__gt=0, is_active=True).select_related('category', 'seller').order_by('name')
    if q:
        products = products.filter(name__icontains=q)
    if category_id:
        products = products.filter(category__id=category_id)
    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.item_count
    return render(request, 'store/shop.html', {
        'products': products,
        'categories': Category.objects.all(),
        'q': q,
        'selected_category': category_id,
        'cart_count': cart_count,
    })


# ── Buyer Dashboard ────────────────────────────────────────────────────
@login_required
def buyer_dashboard(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/buyer_dashboard.html', {
        'username': request.user.username,
        'orders': orders[:5],
        'total_orders': orders.count(),
        'delivered': orders.filter(status='delivered').count(),
        'pending': orders.filter(status__in=['pending', 'confirmed', 'shipped']).count(),
    })


# ── Cart ───────────────────────────────────────────────────────────────
@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return render(request, 'store/cart.html', {'cart': cart})


@login_required
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        if item.quantity < product.stock_qty:
            item.quantity += 1
            item.save()
            messages.success(request, f'{product.name} quantity updated.')
        else:
            messages.warning(request, f'Only {product.stock_qty} units available.')
    else:
        messages.success(request, f'{product.name} added to cart!')
    return redirect(request.META.get('HTTP_REFERER', 'shop'))


@login_required
def cart_remove(request, pk):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    get_object_or_404(CartItem, pk=pk, cart=cart).delete()
    messages.success(request, 'Item removed.')
    return redirect('cart')


@login_required
def cart_update(request, pk):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item = get_object_or_404(CartItem, pk=pk, cart=cart)
    qty = int(request.POST.get('quantity', 1))
    if qty > 0 and qty <= item.product.stock_qty:
        item.quantity = qty
        item.save()
    elif qty <= 0:
        item.delete()
    return redirect('cart')


# ── Checkout ───────────────────────────────────────────────────────────
@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    if not cart.cart_items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('shop')
    if request.method == 'POST':
        ts = timezone.now().strftime('%Y%m%d%H%M%S')
        order = Order.objects.create(
            user=request.user,
            invoice_no=f'ORD-{ts}-{random.randint(10,99)}',
            tracking_id=f'TRK-{random.randint(100000,999999)}',
            full_name=request.POST.get('full_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            pincode=request.POST.get('pincode'),
            payment_method=request.POST.get('payment_method', 'cash'),
            notes=request.POST.get('notes', ''),
        )
        for ci in cart.cart_items.all():
            OrderItem.objects.create(order=order, product=ci.product, quantity=ci.quantity, unit_price=ci.product.selling_price)
            ci.product.stock_qty -= ci.quantity
            ci.product.save()
            if ci.product.seller:
                ci.product.seller.total_revenue += ci.subtotal
                ci.product.seller.save()
        cart.cart_items.all().delete()
        messages.success(request, f'Order placed! Invoice: {order.invoice_no} | Tracking: {order.tracking_id}')
        return redirect('order_detail', pk=order.pk)
    return render(request, 'store/checkout.html', {'cart': cart, 'user': request.user})


# ── Orders ─────────────────────────────────────────────────────────────
@login_required
def order_list(request):
    return render(request, 'store/order_list.html', {'orders': Order.objects.filter(user=request.user).order_by('-created_at')})


@login_required
def order_detail(request, pk):
    return render(request, 'store/order_detail.html', {'order': get_object_or_404(Order, pk=pk, user=request.user)})


# ── Seller Application ─────────────────────────────────────────────────
@login_required
def seller_apply(request):
    if hasattr(request.user, 'seller_profile'):
        messages.info(request, 'You already have a seller application.')
        return redirect('seller_dashboard')
    form = SellerApplicationForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        profile = form.save(commit=False)
        profile.user = request.user
        profile.save()
        messages.success(request, 'Application submitted! You will be notified once approved.')
        return redirect('shop')
    return render(request, 'store/seller_apply.html', {'form': form})


# ── Seller Dashboard ───────────────────────────────────────────────────
@seller_required
def seller_dashboard(request):
    try:
        profile = request.user.seller_profile
    except SellerProfile.DoesNotExist:
        return redirect('seller_apply')

    if profile.status == 'pending':
        return render(request, 'store/seller_pending.html', {'profile': profile})
    if profile.status == 'rejected':
        messages.error(request, f'Your application was rejected: {profile.rejection_reason}')
        return redirect('shop')

    products = Product.objects.filter(seller=profile)
    orders = OrderItem.objects.filter(product__seller=profile).select_related('order', 'product').order_by('-order__created_at')

    monthly_revenue = []
    for i in range(5, -1, -1):
        d = timezone.now().date().replace(day=1) - timedelta(days=i * 30)
        month_orders = OrderItem.objects.filter(
            product__seller=profile,
            order__created_at__year=d.year,
            order__created_at__month=d.month,
            order__status='delivered'
        )
        rev = sum(o.line_total for o in month_orders)
        monthly_revenue.append({'month': d.strftime('%b %Y'), 'revenue': float(rev)})

    context = {
        'profile': profile,
        'products': products,
        'total_products': products.filter(is_active=True).count(),
        'total_orders': orders.values('order').distinct().count(),
        'total_revenue': profile.total_revenue,
        'recent_orders': orders[:10],
        'monthly_revenue': monthly_revenue,
        'low_stock': products.filter(stock_qty__lte=F('reorder_level')).count(),
    }
    return render(request, 'store/seller_dashboard.html', context)


# ── Seller Products ────────────────────────────────────────────────────
@seller_required
def seller_products(request):
    profile = get_object_or_404(SellerProfile, user=request.user)
    products = Product.objects.filter(seller=profile).order_by('name')
    return render(request, 'store/seller_products.html', {'products': products, 'profile': profile})


@seller_required
def seller_product_add(request):
    profile = get_object_or_404(SellerProfile, user=request.user, status='approved')
    form = SellerProductForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        product = form.save(commit=False)
        product.seller = profile
        product.buying_price = 0
        product.save()
        messages.success(request, 'Product added to your store!')
        return redirect('seller_products')
    return render(request, 'store/seller_product_form.html', {'form': form, 'title': 'Add Product', 'profile': profile})


@seller_required
def seller_product_edit(request, pk):
    profile = get_object_or_404(SellerProfile, user=request.user)
    product = get_object_or_404(Product, pk=pk, seller=profile)
    form = SellerProductForm(request.POST or None, request.FILES or None, instance=product)
    if form.is_valid():
        form.save()
        messages.success(request, 'Product updated.')
        return redirect('seller_products')
    return render(request, 'store/seller_product_form.html', {'form': form, 'title': 'Edit Product', 'profile': profile})


@seller_required
def seller_product_delete(request, pk):
    profile = get_object_or_404(SellerProfile, user=request.user)
    product = get_object_or_404(Product, pk=pk, seller=profile)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product removed.')
        return redirect('seller_products')
    return render(request, 'store/confirm_delete.html', {'object': product, 'type': 'Product'})


# ── Seller Orders ──────────────────────────────────────────────────────
@seller_required
def seller_orders(request):
    profile = get_object_or_404(SellerProfile, user=request.user)
    order_items = OrderItem.objects.filter(product__seller=profile).select_related('order', 'product', 'order__user').order_by('-order__created_at')
    return render(request, 'store/seller_orders.html', {'order_items': order_items, 'profile': profile})


@seller_required
def seller_order_update(request, pk):
    profile = get_object_or_404(SellerProfile, user=request.user)
    order = get_object_or_404(Order, pk=pk)
    if OrderItem.objects.filter(order=order, product__seller=profile).exists():
        new_status = request.POST.get('status')
        if new_status in ['confirmed', 'shipped', 'delivered']:
            order.status = new_status
            order.save()
            messages.success(request, f'Order status updated to {new_status}.')
    return redirect('seller_orders')


# ── Admin Seller Management ────────────────────────────────────────────
@admin_required
def admin_sellers(request):
    sellers = SellerProfile.objects.select_related('user').order_by('-applied_at')
    return render(request, 'store/admin_sellers.html', {'sellers': sellers})


@admin_required
def admin_seller_approve(request, pk):
    profile = get_object_or_404(SellerProfile, pk=pk)
    profile.status = 'approved'
    profile.approved_at = timezone.now()
    profile.save()
    seller_group, _ = Group.objects.get_or_create(name='Seller')
    profile.user.groups.add(seller_group)
    messages.success(request, f'{profile.business_name} approved!')
    return redirect('admin_sellers')


@admin_required
def admin_seller_reject(request, pk):
    profile = get_object_or_404(SellerProfile, pk=pk)
    reason = request.POST.get('reason', 'Does not meet requirements.')
    profile.status = 'rejected'
    profile.rejection_reason = reason
    profile.save()
    messages.success(request, f'{profile.business_name} rejected.')
    return redirect('admin_sellers')

# ── Product Detail ─────────────────────────────────────────────────────
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    reviews = product.reviews.select_related('user').all()
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1) if reviews else 0
    user_review = None
    already_reviewed = False
    can_review = False

    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        already_reviewed = user_review is not None
        # Allow review if user has ever ordered this product
        can_review = OrderItem.objects.filter(
            order__user=request.user, product=product
        ).exists() or True   # allow all logged-in users to review

    cart_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.item_count

    related = Product.objects.filter(
        category=product.category, is_active=True, stock_qty__gt=0
    ).exclude(pk=pk)[:4]

    return render(request, 'store/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': len(reviews),
        'user_review': user_review,
        'already_reviewed': already_reviewed,
        'can_review': can_review,
        'cart_count': cart_count,
        'related': related,
        'range5': range(1, 6),
    })


# ── Submit Review ──────────────────────────────────────────────────────
@login_required
def submit_review(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if request.method == 'POST':
        rating = int(request.POST.get('rating', 5))
        title  = request.POST.get('title', '').strip()
        body   = request.POST.get('body', '').strip()
        if body:
            ProductReview.objects.update_or_create(
                product=product, user=request.user,
                defaults={'rating': rating, 'title': title, 'body': body}
            )
            messages.success(request, 'Your review has been submitted!')
        else:
            messages.error(request, 'Review text cannot be empty.')
    return redirect('product_detail', pk=pk)


# ── Delete Review ──────────────────────────────────────────────────────
@login_required
def delete_review(request, pk):
    review = get_object_or_404(ProductReview, pk=pk, user=request.user)
    product_pk = review.product.pk
    review.delete()
    messages.success(request, 'Review deleted.')
    return redirect('product_detail', pk=product_pk)


# ── Buy Now (direct checkout with single product) ──────────────────────
@login_required
def buy_now(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True, stock_qty__gt=0)
    # Add to cart then go to checkout
    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        if item.quantity < product.stock_qty:
            item.quantity += 1
            item.save()
    return redirect('checkout')
