from django.contrib import admin
from .models import AssetCategory, Asset, CustomFieldDefinition, Company, UserProfile

# --- Company Admin (only superuser can manage companies) ---
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'company_id', 'is_active', 'created_at']
    search_fields = ['name', 'company_id']
    # Only superuser can see companies
    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return Company.objects.none()  # regular staff can't see companies

# --- AssetCategory Admin with isolation ---
@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'icon']
    exclude = ('company',)   # hide company from form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.profile.company)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.company = request.user.profile.company
        super().save_model(request, obj, form, change)

# --- Asset Admin with isolation ---
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'serial_number', 'company', 'status', 'assigned_to']
    list_filter = ['status', 'company']
    search_fields = ['name', 'serial_number']
    exclude = ('company',)   # hide company from form

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.profile.company)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.company = request.user.profile.company
        super().save_model(request, obj, form, change)

# --- CustomFieldDefinition Admin with isolation ---
@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ['label', 'name', 'company', 'field_type', 'is_active']
    list_filter = ['field_type', 'is_active', 'company']
    exclude = ('company',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(company=request.user.profile.company)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.company = request.user.profile.company
        super().save_model(request, obj, form, change)

# Optional: UserProfile admin to see which users belong to which company
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company']
    list_filter = ['company']