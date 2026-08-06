from django.contrib import admin, messages
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile
from django import forms
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from .models import (
    District, Sector, Store, Store, FeedType, Animal,
    Measure, Product, Order, Sale, SaleItem, PaymentMethod,
    PaymentStatus, Restock
)
from unfold.admin import ModelAdmin

# Register your models here.

@admin.register(Restock)
class RestockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'cost_per_unit', 'total_cost', 'restocked_by', 'created_at')
    list_filter = ('created_at', 'product__store', 'restocked_by')
    search_fields = ('product__feed_type__name', 'note')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('product',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # new restock
            obj.restocked_by = request.user
        super().save_model(request, obj, form, change)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price')
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'store', 'sold_by','payment_status', 'payment_method', 'created_at', 'total')
    list_filter = ('payment_status', 'payment_method','store', 'sold_by')
    readonly_fields = ('store', 'sold_by', 'payment_status', 'payment_method','created_at')
    inlines = [SaleItemInline]

    def has_add_permission(self, request):
        return False  # Sales should only be created via order confirmation, not manually




class ConfirmOrderForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    payment_status = forms.ChoiceField(choices=PaymentStatus.choices)
    payment_method = forms.ChoiceField(choices=PaymentMethod.choices)


@admin.action(description="Confirm selected orders (deduct stock & record sale)")
def confirm_orders(modeladmin, request, queryset):
    form = None

    if 'apply' in request.POST:
        form = ConfirmOrderForm(request.POST)
        if form.is_valid():
            payment_status = form.cleaned_data['payment_status']
            payment_method = form.cleaned_data['payment_method']

            confirmed_count = 0
            skipped_count = 0

            for order in queryset:
                if order.status != Order.Status.PENDING:
                    skipped_count += 1
                    continue
                try:
                    order.confirm(
                        confirmed_by=request.user,
                        payment_status=payment_status,
                        payment_method=payment_method,
                    )
                    confirmed_count += 1
                except ValidationError as e:
                    skipped_count += 1
                    messages.warning(request, f"Order #{order.pk} skipped: {e}")

            if confirmed_count:
                messages.success(
                    request,
                    f"{confirmed_count} order(s) confirmed — stock updated, sales recorded."
                )
            if skipped_count:
                messages.warning(
                    request,
                    f"{skipped_count} order(s) skipped (already processed or insufficient stock)."
                )
            return None  # back to the changelist

    if not form:
        form = ConfirmOrderForm(
            initial={'_selected_action': queryset.values_list('pk', flat=True)}
        )

    return render(
        request,
        'confirm_orders_intermediate.html',
        context={
            'orders': queryset,
            'form': form,
            'title': 'Confirm Orders',
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        },
    )
    


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'full_name', 'telephone', 'product', 'quantity',
        'unit_price', 'total_price', 'status', 'created_at', 'confirmed_by',
    )
    list_filter = ('status', 'district', 'sector', 'product__store')
    search_fields = ('full_name', 'telephone', 'district', 'sector', 'cell')
    readonly_fields = ('unit_price', 'created_at', 'confirmed_by', 'confirmed_at')
    ordering = ('-created_at',)
    actions = [confirm_orders]


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'district')
    list_filter = ('district',)
    search_fields = ('name',)



@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'sector', 'created_at', 'updated_at')
    list_filter = ('sector',)
    search_fields = ('name', 'manager__username', 'sector__name')
    readonly_fields = ('created_at', 'updated_at')

class FeedTypeInline(admin.TabularInline):
    model = FeedType
    extra = 1


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_preview')
    search_fields = ('name',)
    inlines = [FeedTypeInline]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:50px;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(FeedType)
class FeedTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'animal', 'description')
    list_filter = ('animal',)
    search_fields = ('name', 'animal__name')


@admin.register(Measure)
class MeasureAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation')
    search_fields = ('name', 'abbreviation')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('store', 'feed_type', 'stock_quantity', 'measure','amount', 'cost', 'default_price')
    list_filter = ('store', 'feed_type__animal', 'measure')
    search_fields = ('feed_type__name', 'store__name')

