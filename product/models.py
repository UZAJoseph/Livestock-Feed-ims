from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone




#add model
class District(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Sector(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='sectors')

    def __str__(self):
        return self.name


class Store(models.Model):
    
    name = models.CharField(max_length=100)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='managed_stores',
    )
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name='stores')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Animal(models.Model):
    """e.g. Cow, Dog, Chicken, Pig..."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class FeedType(models.Model):
    """e.g. for Cow: Starter Feed, Grower Feed... for Chicken: Layer Feed, Broiler Finisher..."""
    animal = models.ForeignKey(Animal, on_delete=models.CASCADE, related_name='feed_types')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ('animal', 'name')  # same feed name allowed for different animals

    def __str__(self):
        return f'{self.animal.name} - {self.name}'

class Measure(models.Model):
    """e.g. Kilogram, Gram, Ton, Liter, Bag..."""
    name = models.CharField(max_length=50, unique=True)
    abbreviation = models.CharField(max_length=10, blank=True, help_text="e.g. kg, g, ton, L")

    def __str__(self):
        return self.name

class Product(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
    feed_type = models.ForeignKey(FeedType, on_delete=models.CASCADE, related_name='products')
    amount = models.DecimalField(
        max_digits=6, decimal_places=2,
        help_text="e.g. 25 for a 25kg bag, 50 for a 50kg bag"
    )
    measure = models.ForeignKey(Measure, on_delete=models.PROTECT, related_name='products')
    cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    default_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ('store', 'feed_type', 'amount', 'measure')

    def __str__(self):
        return f"{self.store.name} - {self.feed_type} - {self.amount}{self.measure.abbreviation or self.measure.name} - {self.default_price}"


class PaymentStatus(models.TextChoices):
    PAID = 'paid', 'Paid'
    UNPAID = 'unpaid', 'Unpaid'
    PREPAID = 'prepaid', 'Prepaid'



class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELLED = 'cancelled', 'Cancelled'

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='orders')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    full_name = models.CharField(max_length=150)
    telephone = models.CharField(max_length=20)
    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    cell = models.CharField(max_length=100)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_orders',
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.pk} - {self.full_name} - {self.product} x {self.quantity}"

    @property
    def total_price(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.default_price
        super().save(*args, **kwargs)

    @transaction.atomic
    def confirm(self, confirmed_by, payment_status):
        """Manager/admin confirms the order and decides the payment status."""
        if self.status != Order.Status.PENDING:
            raise ValidationError("Only pending orders can be confirmed.")

        if payment_status not in PaymentStatus.values:
            raise ValidationError("Invalid payment status.")

        sale = Sale.objects.create(
            store=self.product.store,
            sold_by=confirmed_by,
            order=self,
            payment_status=payment_status,
        )

        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=self.quantity,
            unit_price=self.unit_price,
        )  # deducts Product.quantity automatically via SaleItem.save()

        self.status = Order.Status.CONFIRMED
        self.confirmed_by = confirmed_by
        self.confirmed_at = timezone.now()
        self.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])

        return sale

class Sale(models.Model):
    store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name='sales')
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sales_made',
    )
    order = models.OneToOneField(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='sale'
    )
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale #{self.pk} - {self.store} - {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())


# class Sale(models.Model):
#     store = models.ForeignKey(Store, on_delete=models.PROTECT, related_name='sales')
#     sold_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.PROTECT,
#         related_name='sales_made',
#     )
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Sale #{self.pk} - {self.store} - {self.created_at:%Y-%m-%d %H:%M}"

#     @property
#     def total(self):
#         return sum(item.subtotal for item in self.items.all())


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product} x {self.quantity}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.default_price

        is_new = self._state.adding

        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.product_id)

            if is_new and product.quantity < self.quantity:
                raise ValidationError(
                    f"Not enough stock for {product}. Available: {product.quantity}"
                )

            super().save(*args, **kwargs)

            if is_new:
                product.quantity -= self.quantity
                product.save(update_fields=['quantity'])