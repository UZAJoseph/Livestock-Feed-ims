from django.contrib import admin, messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import District, Sector, Store, Store, FeedType, Animal, Measure, Product, Order, Sale, SaleItem


# Register your models here.

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price')
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'store', 'sold_by','payment_status', 'created_at', 'total')
    list_filter = ('payment_status','store', 'sold_by')
    readonly_fields = ('store', 'sold_by', 'created_at')
    inlines = [SaleItemInline]

    def has_add_permission(self, request):
        return False  # Sales should only be created via order confirmation, not manually

    

@admin.action(description="Confirm selected orders (deduct stock & record sale)")
def confirm_orders(modeladmin, request, queryset):
    confirmed_count = 0
    skipped_count = 0

    for order in queryset:
        if order.status != Order.Status.PENDING:
            skipped_count += 1
            continue

        try:
            sale = Sale.objects.create(store=order.product.store, sold_by=request.user)
            SaleItem.objects.create(
                sale=sale,
                product=order.product,
                quantity=order.quantity,
                unit_price=order.unit_price,
            )

            order.status = Order.Status.CONFIRMED
            order.confirmed_by = request.user
            order.confirmed_at = timezone.now()
            order.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])

            confirmed_count += 1

        except ValidationError as e:
            skipped_count += 1
            messages.warning(request, f"Order #{order.pk} skipped: {e.message}")

    if confirmed_count:
        messages.success(request, f"{confirmed_count} order(s) confirmed — stock updated, sales recorded.")
    if skipped_count:
        messages.warning(request, f"{skipped_count} order(s) skipped (already processed or insufficient stock).")


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
    list_display = ('name',)
    search_fields = ('name',)
    inlines = [FeedTypeInline]


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
    list_display = ('store', 'feed_type', 'quantity', 'measure','amount', 'cost', 'default_price')
    list_filter = ('store', 'feed_type__animal', 'measure')
    search_fields = ('feed_type__name', 'store__name')

