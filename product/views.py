from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from .models import Animal, Order, Product, FeedType
from django.db.models import Sum, F, DecimalField, Count
from django.db.models.functions import Coalesce, TruncDate
from django.contrib.admin.views.decorators import staff_member_required
from .models import Order, Sale, SaleItem, Product, Animal, FeedType, Review, District, Sector, Measure, Store
from .forms import RegisterForm, LoginForm,  ReviewForm
from django.utils import timezone
from django.contrib.auth.models import User, Group
from datetime import timedelta
from django.db.models import Sum, Count, F, DecimalField, ExpressionWrapper
from django.db.models.functions import TruncDate, Coalesce
from django.http import JsonResponse
from django.shortcuts import render
from .models import Order, Product



@permission_required('yourapp.can_view_dashboard', login_url='/')
def stock_consumption_data(request):
    """
    Consumption rate (avg units sold/day over trailing 30 days) per product,
    plus estimated days until stockout at current rate.
    """
    days_window = 30
    since = timezone.now() - timedelta(days=days_window)

    consumption = (
        SaleItem.objects
        .filter(sale__created_at__gte=since)
        .values('product_id')
        .annotate(total_sold=Sum('quantity'))
    )
    consumption_map = {c['product_id']: c['total_sold'] for c in consumption}

    products = Product.objects.select_related('feed_type', 'feed_type__animal', 'store', 'measure')

    results = []
    for p in products:
        total_sold = consumption_map.get(p.id, 0)
        daily_rate = float(total_sold) / days_window if total_sold else 0

        if daily_rate > 0:
            days_left = float(p.stock_quantity) / daily_rate
        else:
            days_left = None  # no recent sales — can't estimate

        results.append({
            "product": str(p),
            "store": p.store.name,
            "stock_quantity": float(p.stock_quantity),
            "daily_consumption_rate": round(daily_rate, 2),
            "days_until_stockout": round(days_left, 1) if days_left is not None else None,
            "is_low_stock": p.is_low_stock,
        })

    # Sort so soonest stockouts appear first (None/no-data pushed to the end)
    results.sort(key=lambda r: (r["days_until_stockout"] is None, r["days_until_stockout"]))

    return JsonResponse({"results": results})


@permission_required('yourapp.can_view_dashboard', login_url='/')
def model_summary_data(request):
    counts = {
        "Users": User.objects.count(),
        "Groups": Group.objects.count(),
        "Animals": Animal.objects.count(),
        "Districts": District.objects.count(),
        "Sectors": Sector.objects.count(),
        "Stores": Store.objects.count(),
        "Feed Types": FeedType.objects.count(),
        "Measures": Measure.objects.count(),
        "Products": Product.objects.count(),
        "Orders": Order.objects.count(),
        "Sales": Sale.objects.count(),
        "Reviews": Review.objects.count(),
    }
    return JsonResponse({
        "labels": list(counts.keys()),
        "counts": list(counts.values()),
    })



DECIMAL = DecimalField(max_digits=12, decimal_places=2)

@permission_required('yourapp.can_view_dashboard', login_url='/')
def dashboard(request):
    return render(request, "dashboard.html")

@permission_required('yourapp.can_view_dashboard', login_url='/')
def dashboard_kpis(request):
    """Quick summary numbers shown as cards at the top of the dashboard."""
    sale_items = SaleItem.objects.select_related('product')

    totals = sale_items.aggregate(
        total_sales=Coalesce(
            Sum(F('quantity') * F('unit_price'), output_field=DECIMAL), 0, output_field=DECIMAL
        ),
        total_cost=Coalesce(
            Sum(F('quantity') * F('product__cost'), output_field=DECIMAL), 0, output_field=DECIMAL
        ),
    )

    total_sales = totals['total_sales']
    total_cost = totals['total_cost']
    profit = total_sales - total_cost

    low_stock_feedtypes = (
        Product.objects
        .filter(stock_quantity__lte=F('reorder_level'))
        .values('feed_type')
        .distinct()
        .count()
    )

    return JsonResponse({
        "total_sales": float(total_sales),
        "total_cost": float(total_cost),
        "profit": float(profit),
        "total_orders": Order.objects.count(),
        "pending_orders": Order.objects.filter(status=Order.Status.PENDING).count(),
        "low_stock_products": Product.objects.filter(stock_quantity__lte=F('reorder_level')).count(),
        "low_stock_feedtypes": low_stock_feedtypes,  # new
    })

@permission_required('yourapp.can_view_dashboard', login_url='/')
def sales_summary_data(request):
    """Revenue per day, confirmed orders only."""
    data = (
        Order.objects.filter(status=Order.Status.CONFIRMED)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            total=Sum(F('quantity') * F('unit_price'), output_field=DECIMAL),
            count=Count("id"),
        )
        .order_by("day")
    )
    return JsonResponse({
        "labels": [d["day"].strftime("%b %d") for d in data],
        "totals": [float(d["total"]) for d in data],
        "counts": [d["count"] for d in data],
    })

@permission_required('yourapp.can_view_dashboard', login_url='/')
def top_products_data(request):
    """Top 5 feed types by revenue (Product has no standalone 'name' field)."""
    data = (
        Order.objects.filter(status=Order.Status.CONFIRMED)
        .values("product__feed_type__animal__name", "product__feed_type__name")
        .annotate(total=Sum(F('quantity') * F('unit_price'), output_field=DECIMAL))
        .order_by("-total")[:5]
    )
    return JsonResponse({
        "labels": [f'{d["product__feed_type__animal__name"]} - {d["product__feed_type__name"]}' for d in data],
        "totals": [float(d["total"]) for d in data],
    })


@permission_required('yourapp.can_view_dashboard', login_url='/')
def orders_by_status_data(request):
    status_labels = dict(Order.Status.choices)
    data = Order.objects.values("status").annotate(count=Count("id"))
    return JsonResponse({
        "labels": [status_labels.get(d["status"], d["status"]) for d in data],
        "counts": [d["count"] for d in data],
    })


@permission_required('yourapp.can_view_dashboard', login_url='/')
def revenue_by_customer_data(request):
    data = (
        Order.objects.filter(status=Order.Status.CONFIRMED)
        .values("full_name")
        .annotate(total=Sum(F('quantity') * F('unit_price'), output_field=DECIMAL))
        .order_by("-total")[:10]
    )
    return JsonResponse({
        "labels": [d["full_name"] for d in data],
        "totals": [float(d["total"]) for d in data],
    })





def _base_context(request, **extra):
    context = {
        'animals': Animal.objects.all().order_by('name'),
        'products': Product.objects.select_related('feed_type', 'feed_type__animal', 'store'),
        'register_form': RegisterForm(),
        'login_form': LoginForm(),
        'review_form': ReviewForm(),
        'reviews': Review.objects.select_related('user', 'feed_type').all()[:20],
        'profile': getattr(request.user, 'profile', None) if request.user.is_authenticated else None,
    }
    context.update(extra)
    return context


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, f"Welcome, {user.first_name}! Your account was created.")
            if request.POST.get('next') == 'order':
                request.session['open_order_modal'] = True
            return redirect('index')
        else:
            messages.error(request, "Please fix the errors below.")
            return render(request, 'base.html', _base_context(request, register_form=form, open_modal='register'))
    return redirect('index')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")

            if user.is_staff:
                return redirect('/admin/')

            if request.POST.get('next') == 'order':
                request.session['open_order_modal'] = True
            return redirect('index')
        else:
            messages.error(request, "Please fix the errors below.")
            return render(request, 'base.html', _base_context(request, login_form=form, open_modal='login'))
    return redirect('index')

@login_required(login_url='/')
def review_create(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, "Thanks for your feedback!")
        else:
            messages.error(request, "Please fix the errors below.")
            return render(request, 'base.html', _base_context(request, review_form=form, open_modal='review'))
    return redirect('index')


def index(request):
    context = _base_context(request)
    if request.session.pop('open_order_modal', False):
        context['open_modal'] = 'orderNow'
    return render(request, 'base.html', context)


def logout_view(request):
    auth_logout(request)
    messages.info(request, "You've been logged out.")
    return redirect('index')


@login_required(login_url='/')
def order_form(request):
    profile = getattr(request.user, 'profile', None)

    if request.method == 'POST':
        product_id = request.POST.get('product')
        quantity = request.POST.get('quantity')

        try:
            product = Product.objects.get(pk=product_id)
            quantity = float(quantity)

            if quantity <= 0:
                messages.error(request, "Quantity must be greater than 0.")
            elif quantity > product.stock_quantity:
                messages.error(request, f"Only {product.quantity} available in stock.")
            else:
                Order.objects.create(
                    user=request.user,
                    product=product,
                    quantity=quantity,
                    unit_price=product.default_price,
                    full_name=f"{request.user.first_name} {request.user.last_name}".strip(),
                    telephone=profile.telephone if profile else '',
                    district=profile.district if profile else '',
                    sector=profile.sector if profile else '',
                    cell=profile.cell if profile else '',
                )
                messages.success(request, "Your order has been submitted! We'll contact you shortly to confirm.")
                request.session['open_order_modal'] = True
                return redirect('index')

        except Product.DoesNotExist:
            messages.error(request, "Selected product not found.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity.")

    return render(request, 'base.html', _base_context(request))

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



def animal_list(request):
    animals = Animal.objects.all().order_by('name')
    return render(request, 'base.html', {'animals':animals})



def home(request):
    animals = Animal.objects.all().order_by('name')
    products = Product.objects.select_related('feed_type', 'feed_type__animal', 'store').filter(quantity__gt=0)
    return render(request, 'home.html', {'animals': animals, 'products': products})