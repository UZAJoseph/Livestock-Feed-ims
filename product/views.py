from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.contrib import messages
from .models import Animal, Order, Product, FeedType




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