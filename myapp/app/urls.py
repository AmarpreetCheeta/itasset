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

    path('import/', views.bulk_import, name='bulk_import'),
    path('export/', views.bulk_export, name='bulk_export'),

    path('import/template/', views.download_template, name='import_template'),

    path('report/export/', views.custom_report_export, name='custom_report_export'),

    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/update/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    path('asset/<int:asset_pk>/report-fault/', views.report_fault, name='report_fault'),
    path('fault/<int:fault_pk>/resolve/', views.resolve_fault, name='resolve_fault'),
]