from django.contrib import admin
from django.utils import timezone
from .models import (
    Category, Supplier, Product,
    Customer, Sale, SaleItem,
    PurchaseOrder, PurchaseOrderItem,
    SellerProfile, Order, OrderItem, Cart, CartItem
)


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    readonly_fields = ('line_total',)


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    readonly_fields = ('line_total',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('line_total',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'seller', 'selling_price', 'stock_qty', 'is_active', 'is_low_stock')
    list_filter = ('category', 'is_active', 'seller')
    search_fields = ('name', 'sku')
    readonly_fields = ('profit_margin',)
    list_editable = ('is_active',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'customer', 'grand_total', 'payment_method', 'status', 'sale_date')
    inlines = [SaleItemInline]
    readonly_fields = ('subtotal', 'discount_amount', 'grand_total')
    list_filter = ('status', 'payment_method')
    search_fields = ('invoice_no',)


@admin.register(PurchaseOrder)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'status', 'total_amount', 'order_date')
    inlines = [PurchaseItemInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'user', 'full_name', 'grand_total', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('invoice_no', 'tracking_id', 'full_name')
    inlines = [OrderItemInline]
    readonly_fields = ('subtotal', 'discount_amount', 'grand_total', 'tracking_id', 'invoice_no')
    list_editable = ('status',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'owner_name', 'gst_id', 'status', 'applied_at', 'total_products')
    list_filter = ('status',)
    search_fields = ('business_name', 'gst_id', 'owner_name')
    readonly_fields = ('applied_at', 'total_products', 'total_orders')
    list_editable = ('status',)

    actions = ['approve_sellers', 'reject_sellers']

    def approve_sellers(self, request, queryset):
        queryset.update(status='approved', approved_at=timezone.now())
        # Add to Seller group
        from django.contrib.auth.models import Group
        seller_group, _ = Group.objects.get_or_create(name='Seller')
        for profile in queryset:
            profile.user.groups.add(seller_group)
        self.message_user(request, f'{queryset.count()} seller(s) approved.')
    approve_sellers.short_description = 'Approve selected sellers'

    def reject_sellers(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f'{queryset.count()} seller(s) rejected.')
    reject_sellers.short_description = 'Reject selected sellers'


admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Customer)
admin.site.register(Cart)
admin.site.register(CartItem)