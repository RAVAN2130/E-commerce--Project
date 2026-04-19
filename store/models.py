from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ── Category ──────────────────────────────────────────────────────────
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# ── Supplier ───────────────────────────────────────────────────────────
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField()

    def __str__(self):
        return self.name


# ── Product ────────────────────────────────────────────────────────────
class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    seller = models.ForeignKey('SellerProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def profit_margin(self):
        if self.buying_price and self.buying_price > 0:
            return round(((self.selling_price - self.buying_price) / self.buying_price) * 100, 2)
        return 0

    @property
    def is_low_stock(self):
        return self.stock_qty <= self.reorder_level


# ── Customer ───────────────────────────────────────────────────────────
class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ── Sale ───────────────────────────────────────────────────────────────
class Sale(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
    ]
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('credit', 'Credit'),
    ]

    invoice_no = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    sale_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='completed')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cash')
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.invoice_no

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def discount_amount(self):
        return round(self.subtotal * self.discount / 100, 2)

    @property
    def grand_total(self):
        return round(self.subtotal - self.discount_amount, 2)


# ── Sale Item ──────────────────────────────────────────────────────────
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def line_total(self):
        if self.unit_price and self.quantity:
            return self.unit_price * self.quantity
        return 0

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.selling_price
        super().save(*args, **kwargs)


# ── Purchase Order ─────────────────────────────────────────────────────
class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('ordered', 'Ordered'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    ordered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    order_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ordered')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"PO-{self.id} | {self.supplier}"


# ── Purchase Order Item ────────────────────────────────────────────────
class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        if self.unit_cost and self.quantity:
            return self.unit_cost * self.quantity
        return 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.order.status == 'received':
            self.product.stock_qty += self.quantity
            self.product.save()


# ── Seller Profile ─────────────────────────────────────────────────────
class SellerProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    business_name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    gst_id = models.CharField(max_length=15, unique=True, help_text='15-digit GST number')
    pan_number = models.CharField(max_length=10, help_text='10-digit PAN number')
    business_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    business_type = models.CharField(max_length=100, help_text='e.g. Electronics, Clothing, Food')
    bio = models.TextField(help_text='Brief description of your business')
    bank_account = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=11)
    profile_photo = models.ImageField(upload_to='sellers/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    terms_accepted = models.BooleanField(default=False)
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.business_name} ({self.status})"

    @property
    def total_products(self):
        return self.products.filter(is_active=True).count()

    @property
    def total_orders(self):
        return OrderItem.objects.filter(product__seller=self).values('order').distinct().count()


# ── Cart ───────────────────────────────────────────────────────────────
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.username}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.cart_items.all())

    @property
    def item_count(self):
        return sum(item.quantity for item in self.cart_items.all())


# ── Cart Item ──────────────────────────────────────────────────────────
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='cart_items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.product.selling_price * self.quantity


# ── Order ──────────────────────────────────────────────────────────────
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_CHOICES = [
        ('cash', 'Cash on Delivery'),
        ('upi', 'UPI'),
        ('card', 'Card'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    invoice_no = models.CharField(max_length=50, unique=True)
    tracking_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cash')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Order {self.invoice_no} — {self.user.username}"

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.order_items.all())

    @property
    def discount_amount(self):
        return round(self.subtotal * self.discount / 100, 2)

    @property
    def grand_total(self):
        return round(self.subtotal - self.discount_amount, 2)


# ── Order Item ─────────────────────────────────────────────────────────
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

# ── Product Review ─────────────────────────────────────────────────────
class ProductReview(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating  = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    title   = models.CharField(max_length=120, blank=True)
    body    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')   # one review per product per user
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.product.name} ({self.rating}★)"
