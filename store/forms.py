from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from .models import (
    Product, Customer, Sale, SaleItem, Supplier,
    PurchaseOrder, PurchaseOrderItem, SellerProfile
)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'sku', 'description',
                  'buying_price', 'selling_price', 'stock_qty',
                  'reorder_level', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class SellerProductForm(forms.ModelForm):
    """Used by sellers — no buying_price or supplier fields shown"""
    class Meta:
        model = Product
        fields = ['name', 'category', 'sku', 'description',
                  'selling_price', 'stock_qty', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address'].required = False


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'email', 'phone', 'address']


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer', 'sale_date', 'status', 'payment_method', 'discount', 'notes']
        widgets = {
            'sale_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].required = False
        self.fields['notes'].required = False
        self.fields['discount'].initial = 0
        if self.instance and self.instance.sale_date:
            self.initial['sale_date'] = self.instance.sale_date.strftime('%Y-%m-%dT%H:%M')


class SaleItemFormSet_Base(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        filled = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data.get('product') and form.cleaned_data.get('quantity'):
                    filled += 1
        if filled == 0:
            raise forms.ValidationError('Please add at least one item to the sale.')


SaleItemFormSet = inlineformset_factory(
    Sale, SaleItem,
    fields=['product', 'quantity', 'unit_price'],
    formset=SaleItemFormSet_Base,
    extra=3,
    can_delete=True
)


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'order_date', 'status']
        widgets = {
            'order_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.order_date:
            self.initial['order_date'] = self.instance.order_date.strftime('%Y-%m-%dT%H:%M')


PurchaseItemFormSet = inlineformset_factory(
    PurchaseOrder, PurchaseOrderItem,
    fields=['product', 'quantity', 'unit_cost'],
    extra=3,
    can_delete=True
)


class SellerApplicationForm(forms.ModelForm):
    terms_accepted = forms.BooleanField(
        required=True,
        label='I agree to the Terms & Conditions and Seller Policy'
    )

    class Meta:
        model = SellerProfile
        fields = [
            'business_name', 'owner_name', 'email', 'phone',
            'gst_id', 'pan_number', 'business_address', 'city',
            'state', 'pincode', 'business_type', 'bio',
            'bank_account', 'bank_name', 'ifsc_code',
            'profile_photo', 'terms_accepted'
        ]
        widgets = {
            'business_address': forms.Textarea(attrs={'rows': 2}),
            'bio': forms.Textarea(attrs={'rows': 3}),
        }