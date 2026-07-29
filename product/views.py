from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.contrib import messages
from .models import Animal, Order, Product, FeedType
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.contrib.admin.views.decorators import staff_member_required
from .models import Order, Sale, SaleItem, Product, Animal, FeedType




def _apply_common_filters(qs, request, animal_field, feedtype_field, date_field=None):
    animal_id = request.GET.get('animal')
    feedtype_id = request.GET.get('feed_type')

    if animal_id:
        qs = qs.filter(**{animal_field: animal_id})
    if feedtype_id:
        qs = qs.filter(**{feedtype_field: feedtype_id})

    if date_field:
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            qs = qs.filter(**{f'{date_field}__date__gte': date_from})
        if date_to:
            qs = qs.filter(**{f'{date_field}__date__lte': date_to})

    return qs


@staff_member_required
def reports_dashboard(request):
    decimal_zero = DecimalField(max_digits=12, decimal_places=2)

    # ---------- STOCK (valued at COST) ----------
    stock_qs = Product.objects.select_related('feed_type__animal', 'measure')
    stock_qs = _apply_common_filters(
        stock_qs, request,
        animal_field='feed_type__animal_id',
        feedtype_field='feed_type_id',
    )
    stock_by_measure = (
        stock_qs
        .values('measure__name', 'measure__abbreviation')
        .annotate(
            total_quantity=Coalesce(Sum('quantity'), 0, output_field=decimal_zero),
            total_value=Coalesce(
                Sum(F('quantity') * F('cost'), output_field=decimal_zero), 0,
                output_field=decimal_zero,
            ),
        )
        .order_by('measure__name')
    )

    # ---------- ORDERS (valued at unit_price) ----------
    orders_qs = Order.objects.select_related('product__feed_type__animal', 'product__measure')
    orders_qs = _apply_common_filters(
        orders_qs, request,
        animal_field='product__feed_type__animal_id',
        feedtype_field='product__feed_type_id',
        date_field='created_at',
    )
    status_filter = request.GET.get('order_status')
    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)

    orders_by_measure = (
        orders_qs
        .values('product__measure__name', 'product__measure__abbreviation')
        .annotate(
            total_quantity=Coalesce(Sum('quantity'), 0, output_field=decimal_zero),
            total_value=Coalesce(
                Sum(F('quantity') * F('unit_price'), output_field=decimal_zero), 0,
                output_field=decimal_zero,
            ),
        )
        .order_by('product__measure__name')
    )

    # ---------- SALES (valued at unit_price, dated by sale.created_at) ----------
    sale_items_qs = SaleItem.objects.select_related(
        'product__feed_type__animal', 'product__measure', 'sale'
    )
    sale_items_qs = _apply_common_filters(
        sale_items_qs, request,
        animal_field='product__feed_type__animal_id',
        feedtype_field='product__feed_type_id',
        date_field='sale__created_at',
    )
    payment_status = request.GET.get('payment_status')
    payment_method = request.GET.get('payment_method')
    if payment_status:
        sale_items_qs = sale_items_qs.filter(sale__payment_status=payment_status)
    if payment_method:
        sale_items_qs = sale_items_qs.filter(sale__payment_method=payment_method)

    sales_by_measure = (
        sale_items_qs
        .values('product__measure__name', 'product__measure__abbreviation')
        .annotate(
            total_quantity=Coalesce(Sum('quantity'), 0, output_field=decimal_zero),
            total_value=Coalesce(
                Sum(F('quantity') * F('unit_price'), output_field=decimal_zero), 0,
                output_field=decimal_zero,
            ),
        )
        .order_by('product__measure__name')
    )

    context = {
        'stock_by_measure': stock_by_measure,
        'orders_by_measure': orders_by_measure,
        'sales_by_measure': sales_by_measure,
        'animals': Animal.objects.all(),
        'feed_types': FeedType.objects.select_related('animal').all(),
        'order_statuses': Order.Status.choices,
        'filters': request.GET,
    }
    return render(request, 'h1.html', context)

# Create your views here.

def feed_selector_page(request):
    animals = Animal.objects.all()
    return render(request, 'home.html', {'animals':animals})

def get_feed_types(request, animal_id):
    feed_types = FeedType.objects.filter(animal_id=animal_id).values('id', 'name')
    return JsonResponse({'feed_types':list(feed_types)})


def get_feed_description(request, feedtype_id):
    """Return the description of a single feed type."""
    try:
        feed_type = FeedType.objects.get(id=feedtype_id)
    except FeedType.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    return JsonResponse({
        'name': feed_type.name,
        'description': feed_type.description or 'No description available.',
    })


def order_form(request):
    products = Product.objects.select_related('feed_type', 'feed_type__animal', 'store').filter(quantity__gt=0)

    if request.method == 'POST':
        product_id = request.POST.get('product')
        quantity = request.POST.get('quantity')
        full_name = request.POST.get('full_name')
        telephone = request.POST.get('telephone')
        district = request.POST.get('district')
        sector = request.POST.get('sector')
        cell = request.POST.get('cell')

        try:
            product = Product.objects.get(pk=product_id)
            quantity = float(quantity)

            if quantity <= 0:
                messages.error(request, "Quantity must be greater than 0.")
            elif quantity > product.quantity:
                messages.error(request, f"Only {product.quantity} available in stock.")
            else:
                Order.objects.create(
                    product=product,
                    quantity=quantity,
                    unit_price=product.default_price,
                    full_name=full_name,
                    telephone=telephone,
                    district=district,
                    sector=sector,
                    cell=cell,
                )
                messages.success(request, "Your order has been submitted! We'll contact you shortly to confirm.")
                return redirect('home')

        except Product.DoesNotExist:
            messages.error(request, "Selected product not found.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity.")

    return render(request, 'home.html', {'products': products})
    

def animal_list(request):
    animals = Animal.objects.all().order_by('name')
    return render(request, 'home.html', {'animals':animals})



def home(request):
    animals = Animal.objects.all().order_by('name')
    products = Product.objects.select_related('feed_type', 'feed_type__animal', 'store').filter(quantity__gt=0)
    return render(request, 'home.html', {'animals': animals, 'products': products})