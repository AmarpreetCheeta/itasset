from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from app.models import Asset, AssetCategory, CustomFieldDefinition
from app.forms import SignUpForm, create_dynamic_asset_form, CustomFieldDefinitionForm

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to IT Asset Management.')
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def dashboard(request):
    # Statistics
    total_assets = Asset.objects.count()
    available_assets = Asset.objects.filter(status='available').count()
    assigned_assets = Asset.objects.filter(status='assigned').count()
    maintenance_assets = Asset.objects.filter(status='maintenance').count()
    retired_assets = Asset.objects.filter(status='retired').count()
    
    # Assets by category
    categories = AssetCategory.objects.annotate(asset_count=Count('assets'))
    
    # Recent assets
    recent_assets = Asset.objects.select_related('category', 'assigned_to')[:10]
    
    # Assets expiring warranty in next 30 days
    today = timezone.now().date()
    thirty_days_later = today + timedelta(days=30)
    expiring_warranty = Asset.objects.filter(
        warranty_expiry__gte=today,
        warranty_expiry__lte=thirty_days_later
    ).count()
    
    # Total value
    total_value = Asset.objects.aggregate(total=Sum('purchase_cost'))['total'] or 0
    
    context = {
        'total_assets': total_assets,
        'available_assets': available_assets,
        'assigned_assets': assigned_assets,
        'maintenance_assets': maintenance_assets,
        'retired_assets': retired_assets,
        'categories': categories,
        'recent_assets': recent_assets,
        'expiring_warranty': expiring_warranty,
        'total_value': total_value,
    }
    return render(request, 'dashboard.html', context)

@login_required
def asset_list(request):
    assets = Asset.objects.select_related('category', 'assigned_to').all()
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        assets = assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(model_number__icontains=search_query)
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        assets = assets.filter(category_id=category_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(assets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = AssetCategory.objects.all()
    status_choices = Asset.STATUS_CHOICES
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'status_choices': status_choices,
        'search_query': search_query,
        'category_filter': category_filter,
        'status_filter': status_filter,
    }
    return render(request, 'asset_list.html', context)

@login_required
def asset_create(request):
    category_id = request.GET.get('category')
    category = None
    if category_id:
        category = get_object_or_404(AssetCategory, id=category_id)
    
    DynamicForm = create_dynamic_asset_form(category=category)
    
    if request.method == 'POST':
        form = DynamicForm(request.POST)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.created_by = request.user
            
            # Extract custom fields
            custom_attrs = {}
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('custom_'):
                    key = field_name.replace('custom_', '')
                    if value is not None and value != '':
                        custom_attrs[key] = value
            
            asset.custom_attrs = custom_attrs
            asset.save()
            messages.success(request, f'Asset "{asset.name}" created successfully!')
            return redirect('asset_detail', pk=asset.pk)
    else:
        form = DynamicForm()
    
    categories = AssetCategory.objects.all()
    return render(request, 'asset_form.html', {'form': form, 'title': 'Create Asset', 'categories': categories})

@login_required
def asset_update(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    DynamicForm = create_dynamic_asset_form(instance=asset, category=asset.category)
    
    if request.method == 'POST':
        form = DynamicForm(request.POST, instance=asset)
        if form.is_valid():
            asset = form.save(commit=False)
            
            # Extract custom fields
            custom_attrs = {}
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('custom_'):
                    key = field_name.replace('custom_', '')
                    if value is not None and value != '':
                        custom_attrs[key] = value
            
            asset.custom_attrs = custom_attrs
            asset.save()
            messages.success(request, f'Asset "{asset.name}" updated successfully!')
            return redirect('asset_detail', pk=asset.pk)
    else:
        form = DynamicForm(instance=asset)
    
    categories = AssetCategory.objects.all()
    return render(request, 'asset_form.html', {'form': form, 'title': 'Update Asset', 'asset': asset, 'categories': categories})

@login_required
def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    
    # Get custom field definitions to display
    custom_definitions = CustomFieldDefinition.objects.filter(is_active=True)
    if asset.category:
        custom_definitions = custom_definitions.filter(Q(category=asset.category) | Q(category__isnull=True))
    
    custom_fields = []
    for definition in custom_definitions:
        value = asset.custom_attrs.get(definition.name, '')
        if value:
            custom_fields.append({
                'label': definition.label,
                'value': value,
                'type': definition.field_type
            })
    
    return render(request, 'asset_detail.html', {'asset': asset, 'custom_fields': custom_fields})

@login_required
def asset_delete(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    if request.method == 'POST':
        asset_name = asset.name
        asset.delete()
        messages.success(request, f'Asset "{asset_name}" deleted successfully!')
        return redirect('asset_list')
    return render(request, 'asset_confirm_delete.html', {'asset': asset})

@user_passes_test(lambda u: u.is_staff)
def custom_field_list(request):
    fields = CustomFieldDefinition.objects.all()
    return render(request, 'custom_fields_list.html', {'fields': fields})

@user_passes_test(lambda u: u.is_staff)
def custom_field_create(request):
    if request.method == 'POST':
        form = CustomFieldDefinitionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Custom field created successfully!')
            return redirect('custom_field_list')
    else:
        form = CustomFieldDefinitionForm()
    return render(request, 'custom_field_form.html', {'form': form, 'title': 'Create Custom Field'})

@user_passes_test(lambda u: u.is_staff)
def custom_field_update(request, pk):
    field = get_object_or_404(CustomFieldDefinition, pk=pk)
    if request.method == 'POST':
        form = CustomFieldDefinitionForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, 'Custom field updated successfully!')
            return redirect('custom_field_list')
    else:
        form = CustomFieldDefinitionForm(instance=field)
    return render(request, 'custom_field_form.html', {'form': form, 'title': 'Update Custom Field', 'field': field})

@user_passes_test(lambda u: u.is_staff)
def custom_field_delete(request, pk):
    field = get_object_or_404(CustomFieldDefinition, pk=pk)
    if request.method == 'POST':
        field.delete()
        messages.success(request, 'Custom field deleted successfully!')
        return redirect('custom_field_list')
    return render(request, 'custom_field_confirm_delete.html', {'field': field})