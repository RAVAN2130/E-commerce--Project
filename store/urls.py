from django.urls import path
from . import views

urlpatterns = [
    # ── Core ───────────────────────────────────
    path('', views.dashboard, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # ── Products ───────────────────────────────
    path('products/', views.product_list, name='product_list'),
    path('products/new/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),

    # ── Sales ──────────────────────────────────
    path('sales/', views.sale_list, name='sale_list'),
    path('sales/new/', views.sale_create, name='sale_create'),
    path('sales/<int:pk>/', views.sale_detail, name='sale_detail'),

    # ── Customers ──────────────────────────────
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/new/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/edit/', views.customer_update, name='customer_update'),

    # ── Suppliers ──────────────────────────────
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/new/', views.supplier_create, name='supplier_create'),

    # ── Purchases ──────────────────────────────
    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/new/', views.purchase_create, name='purchase_create'),

    # ── Reports ────────────────────────────────
    path('reports/', views.reports, name='reports'),

    # ── Buyer ──────────────────────────────────
    path('register/', views.register, name='register'),
    path('shop/', views.shop, name='shop'),
    path('buyer/dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),

    # ── Seller ─────────────────────────────────
    path('seller/apply/', views.seller_apply, name='seller_apply'),
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/products/', views.seller_products, name='seller_products'),
    path('seller/products/add/', views.seller_product_add, name='seller_product_add'),
    path('seller/products/<int:pk>/edit/', views.seller_product_edit, name='seller_product_edit'),
    path('seller/products/<int:pk>/delete/', views.seller_product_delete, name='seller_product_delete'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/orders/<int:pk>/update/', views.seller_order_update, name='seller_order_update'),

    # ── Product Detail & Reviews ────────────
    path('shop/<int:pk>/', views.product_detail, name='product_detail'),
    path('shop/<int:pk>/review/', views.submit_review, name='submit_review'),
    path('reviews/<int:pk>/delete/', views.delete_review, name='delete_review'),
    path('shop/<int:pk>/buy-now/', views.buy_now, name='buy_now'),

    # ── Admin Seller Management ─────────────────
    path('admin-sellers/', views.admin_sellers, name='admin_sellers'),
    path('admin-sellers/<int:pk>/approve/', views.admin_seller_approve, name='admin_seller_approve'),
    path('admin-sellers/<int:pk>/reject/', views.admin_seller_reject, name='admin_seller_reject'),
]