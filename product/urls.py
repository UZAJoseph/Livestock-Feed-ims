from django.urls import path
from . import views


urlpatterns = [
    path('index/', views.index, name='index'),
     path('feeds/', views.feed_selector_page, name='feed_selector_page'),
     path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('feeds/animal/<int:animal_id>/feed-types/', views.get_feed_types, name='get_feed_types'),
    path('feeds/feed-type/<int:feedtype_id>/description/', views.get_feed_description, name='get_feed_description'),
    path("order/", views.order_form, name="order_form"),
    path('', views.home, name='home'),
    path('animals/', views.animal_list, name ='animal_list')
]

