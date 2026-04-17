from django.contrib import admin
from app.models import AssetCategory, Asset, CustomFieldDefinition

@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'created_at']
    search_fields = ['name']

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'serial_number', 'category', 'status', 'assigned_to', 'purchase_cost']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['name', 'serial_number', 'manufacturer']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'serial_number', 'category', 'status')
        }),
        ('Hardware Details', {
            'fields': ('manufacturer', 'model_number')
        }),
        ('Financial Details', {
            'fields': ('purchase_date', 'purchase_cost', 'warranty_expiry')
        }),
        ('Assignment', {
            'fields': ('assigned_to', 'assigned_date', 'location')
        }),
        ('Additional', {
            'fields': ('notes', 'custom_attrs', 'created_by')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ['label', 'name', 'field_type', 'is_required', 'category', 'is_active']
    list_filter = ['field_type', 'is_required', 'category', 'is_active']
    search_fields = ['label', 'name']