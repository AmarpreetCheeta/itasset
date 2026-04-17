from django.urls import path
from app import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/create/', views.asset_create, name='asset_create'),
    path('assets/<int:pk>/', views.asset_detail, name='asset_detail'),
    path('assets/<int:pk>/update/', views.asset_update, name='asset_update'),
    path('assets/<int:pk>/delete/', views.asset_delete, name='asset_delete'),
    path('custom-fields/', views.custom_field_list, name='custom_field_list'),
    path('custom-fields/create/', views.custom_field_create, name='custom_field_create'),
    path('custom-fields/<int:pk>/update/', views.custom_field_update, name='custom_field_update'),
    path('custom-fields/<int:pk>/delete/', views.custom_field_delete, name='custom_field_delete'),
]