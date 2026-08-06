from django.urls import path
from . import views


urlpatterns = [
    path('api/model-summary/', views.model_summary_data, name='model_summary_data'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/dashboard-kpis/", views.dashboard_kpis, name="dashboard_kpis"),
    path("api/sales-summary/", views.sales_summary_data, name="sales_summary_data"),
    path("api/top-products/", views.top_products_data, name="top_products_data"),
    path("api/orders-by-status/", views.orders_by_status_data, name="orders_by_status_data"),
    path("api/revenue-by-customer/", views.revenue_by_customer_data, name="revenue_by_customer_data"),
    path("api/stock-consumption/", views.stock_consumption_data, name="stock_consumption_data"),
    path('review/', views.review_create, name='review_create'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('index/', views.home, name='home'),
    path('feeds/', views.feed_selector_page, name='feed_selector_page'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('feeds/animal/<int:animal_id>/feed-types/', views.get_feed_types, name='get_feed_types'),
    path('feeds/feed-type/<int:feedtype_id>/description/', views.get_feed_description, name='get_feed_description'),
    path("order/", views.order_form, name="order_form"),
    path('', views.index, name='index'),
    path('animals/', views.animal_list, name='animal_list'),
]