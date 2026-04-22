from django.contrib import admin
from .models import AssetCategory, Asset, CustomFieldDefinition, Company, UserProfile, FaultRecord


class FaultRecordInline(admin.TabularInline):
    model = FaultRecord
    extra = 0
    readonly_fields = ['reported_date', 'reported_by']
    fields = ['fault_description', 'severity', 'is_resolved', 'repair_cost', 'repaired_date']
    can_delete = False
    show_change_link = True



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
    # exclude = ('company',)   # hide company from form

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
    list_display = ['name', 'serial_number', 'company', 'is_faulty_badge', 'status', 'assigned_to_name']
    list_filter = ['status', 'company']
    search_fields = ['name', 'serial_number']
    inlines = [FaultRecordInline]
    # exclude = ('company',)   # hide company from form

    def is_faulty_badge(self, obj):
        if obj.status == 'faulty':
            return '⚠️ Faulty'
        return '✓ Operational'
    is_faulty_badge.short_description = 'Fault Status'

    # Optional: add action to mark as faulty
    actions = ['mark_as_faulty']
    
    def mark_as_faulty(self, request, queryset):
        updated = queryset.update(status='faulty')
        self.message_user(request, f'{updated} asset(s) marked as faulty.')
    mark_as_faulty.short_description = "Mark selected assets as Faulty"

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
    # exclude = ('company',)

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


@admin.register(FaultRecord)
class FaultRecordAdmin(admin.ModelAdmin):
    list_display = ['asset', 'reported_by', 'reported_date', 'severity', 'is_resolved', 'repair_cost']
    list_filter = ['severity', 'is_resolved', 'reported_date']
    search_fields = ['asset__name', 'asset__serial_number', 'fault_description']
    readonly_fields = ['reported_date', 'asset', 'reported_by']
    fieldsets = (
        ('Fault Information', {
            'fields': ('asset', 'reported_by', 'reported_date', 'fault_description', 'severity')
        }),
        ('Resolution Details', {
            'fields': ('is_resolved', 'repaired_date', 'repaired_by', 'repair_cost', 'repair_notes')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # new fault
            obj.reported_by = request.user
        super().save_model(request, obj, form, change)

