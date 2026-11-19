from django.urls import path
from .views import ticket_list_view, ticket_create_view, ticket_detail_view

urlpatterns = [
    path('', ticket_list_view, name='ticket_list'),
    path('create/', ticket_create_view, name='ticket_create'),
    path('ticket/<int:pk>/', ticket_detail_view, name='ticket_detail'),
]