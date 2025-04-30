# orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('create/', views.create_medicine_order, name='create_medicine_order'),
    # Add other URLs later for viewing/sharing orders
    path('my-orders/', views.view_medicine_orders, name='view_medicine_orders'),
    path('download/<int:order_id>/', views.download_order_pdf, name='download_order_pdf'),
    path('my-issued/', views.view_issued_orders, name='view_issued_orders')
]