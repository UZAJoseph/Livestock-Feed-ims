from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # urls.py
path('my-dashboard/', views.client_dashboard, name='client_dashboard'),
path('my-dashboard/data/', views.client_dashboard_data, name='client_dashboard_data'),
    path('dashboard/transfer-action/<int:pk>/', views.admin_transfer_action_ajax, name='admin_transfer_action_ajax'),
    path('dashboard/transfer-stats/', views.transfer_stats_data, name='transfer_stats_data'),
path('dashboard/transfer-list/', views.transfer_list_data, name='transfer_list_data'),
    path('transfer/request/', views.transfer_request_create, name='transfer_request_create'),
path('transfer/store-products/<int:store_id>/', views.get_store_products, name='get_store_products'),
path('transfer/my-requests/', views.my_transfer_requests, name='my_transfer_requests'),
path('transfer/source-review/<int:pk>/', views.transfer_source_review, name='transfer_source_review'),
path('transfer/admin/', views.admin_transfer_requests, name='admin_transfer_requests'),
path('transfer/admin-review/<int:pk>/', views.admin_transfer_review, name='admin_transfer_review'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('api/payment-status/', views.payment_status_data, name='payment_status_data'),
    path('api/payment-method/', views.payment_method_data, name='payment_method_data'),
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
    path('feeds/', views.feed_selector_page, name='feed_selector_page'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('feeds/animal/<int:animal_id>/feed-types/', views.get_feed_types, name='get_feed_types'),
    path('feeds/feed-type/<int:feedtype_id>/description/', views.get_feed_description, name='get_feed_description'),
    path("order/", views.order_form, name="order_form"),
    path('', views.index, name='index'),
    path('animals/', views.animal_list, name='animal_list'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)