from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta, date
from app.models import Asset, AssetCategory, CustomFieldDefinition, Company, UserProfile, FaultRecord
from app.forms import SignUpForm, create_dynamic_asset_form, CustomFieldDefinitionForm, CompanyLoginForm, ReportForm, AssetCategoryForm, FaultReportForm
import pandas as pd
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView



def serialize_custom_value(value):
    """Convert non-JSON-serializable types to JSON-serializable ones."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            company_id = form.cleaned_data.get('company_id')
            # Validate company
            try:
                company = Company.objects.get(company_id=company_id, is_active=True)
            except Company.DoesNotExist:
                form.add_error('company_id', 'Invalid Company ID. Please check with your administrator.')
                # Re-render the form with error
                return render(request, 'registration/signup.html', {'form': form})
            
            # Create user but don't save to DB yet
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()
            # Create user profile
            UserProfile.objects.create(user=user, company=company)
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to IT Asset Management.')
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = CompanyLoginForm(request, data=request.POST)
        if form.is_valid():
            company_id = form.cleaned_data.get('company_id')
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Validate company exists and is active (extra check before authentication)
            try:
                company = Company.objects.get(company_id=company_id, is_active=True)
            except Company.DoesNotExist:
                form.add_error(None, "Invalid company ID or company is inactive.")
                return render(request, 'registration/login.html', {'form': form})
            
            # Authenticate using custom backend
            user = authenticate(request, username=username, password=password, company_id=company_id)
            
            if user is not None:
                # Additional user validation
                if not user.is_active:
                    form.add_error(None, "Your account is disabled. Please contact support.")
                elif not hasattr(user, 'profile') or user.profile.company != company:
                    form.add_error(None, "User does not belong to this company.")
                else:
                    # All checks passed
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
                    return redirect('dashboard')
            else:
                form.add_error(None, "Invalid company ID, username, or password.")
    else:
        form = CompanyLoginForm()
    
    return render(request, 'registration/login.html', {'form': form})



@login_required
def dashboard(request):
    # Statistics
    total_assets = Asset.objects.filter(company=request.user.profile.company).count()
    available_assets = Asset.objects.filter(status='available', company=request.user.profile.company).count()
    assigned_assets = Asset.objects.filter(status='assigned', company=request.user.profile.company).count()
    maintenance_assets = Asset.objects.filter(status='maintenance', company=request.user.profile.company).count()
    retired_assets = Asset.objects.filter(status='retired', company=request.user.profile.company).count()
    faulty_assets = Asset.objects.filter(company=request.user.profile.company, status='faulty').count()
    
    # Assets by category
    categories = AssetCategory.objects.filter(company=request.user.profile.company).annotate(asset_count=Count('assets'))
    
    # Recent assets
    recent_assets = Asset.objects.filter(company=request.user.profile.company).select_related('category')[:10]
    
    # Assets expiring warranty in next 30 days
    today = timezone.now().date()
    thirty_days_later = today + timedelta(days=30)
    expiring_warranty = Asset.objects.filter(
        warranty_expiry__gte=today,
        warranty_expiry__lte=thirty_days_later,
        company=request.user.profile.company
    ).count()
    
    # Total value
    total_value = Asset.objects.filter(company=request.user.profile.company).aggregate(total=Sum('purchase_cost'))['total'] or 0
    
    context = {
        'total_assets': total_assets,
        'available_assets': available_assets,
        'assigned_assets': assigned_assets,
        'maintenance_assets': maintenance_assets,
        'retired_assets': retired_assets,
        'categories': categories,
        'recent_assets': recent_assets,
        'expiring_warranty': expiring_warranty,
        'faulty_assets': faulty_assets,
        'total_value': total_value,
    }
    return render(request, 'dashboard.html', context)

@login_required
def asset_list(request):
    company = request.user.profile.company # Added: 20 April 2026
    assets = Asset.objects.filter(company=company).select_related('category')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        assets = assets.filter(
            Q(name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(manufacturer__icontains=search_query) |
            Q(model_number__icontains=search_query) |
            Q(assigned_to_name__icontains=search_query) 
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        assets = assets.filter(category_id=category_filter, company=request.user.profile.company)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        assets = assets.filter(status=status_filter, company=request.user.profile.company)
    
    # Pagination
    paginator = Paginator(assets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = AssetCategory.objects.filter(company=request.user.profile.company)
    status_choices = Asset.STATUS_CHOICES

    custom_fields = CustomFieldDefinition.objects.filter(company=company, is_active=True)
    
    context = {
        'page_obj': page_obj,
        'custom_fields': custom_fields,
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
        category = get_object_or_404(AssetCategory, id=category_id, company=request.user.profile.company)
    
    DynamicForm = create_dynamic_asset_form(category=category)
    
    if request.method == 'POST':
        form = DynamicForm(request.POST)
        form.fields['category'].queryset = AssetCategory.objects.filter(company=request.user.profile.company)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.created_by = request.user
            asset.company = request.user.profile.company
            
            # Extract custom fields
            custom_attrs = {}
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('custom_'):
                    key = field_name.replace('custom_', '')
                    # Convert non-serializable values (like date) to string
                    custom_attrs[key] = serialize_custom_value(value) if value is not None else ''
            
            asset.custom_attrs = custom_attrs
            asset.save()
            messages.success(request, f'Asset "{asset.name}" created successfully!')
            return redirect('asset_detail', pk=asset.pk)
    else:
        form = DynamicForm()
        form.fields['category'].queryset = AssetCategory.objects.filter(company=request.user.profile.company)
    
    categories = AssetCategory.objects.filter(company=request.user.profile.company)
    return render(request, 'asset_form.html', {'form': form, 'title': 'Create Asset', 'categories': categories})

@login_required
def asset_update(request, pk):
    asset = get_object_or_404(Asset, pk=pk, company=request.user.profile.company)
    DynamicForm = create_dynamic_asset_form(instance=asset, category=asset.category)
    
    if request.method == 'POST':
        form = DynamicForm(request.POST, instance=asset)
        form.fields['category'].queryset = AssetCategory.objects.filter(company=request.user.profile.company)
        if form.is_valid():
            asset = form.save(commit=False)
            
            # Extract custom fields
            custom_attrs = {}
            for field_name, value in form.cleaned_data.items():
                if field_name.startswith('custom_'):
                    key = field_name.replace('custom_', '')
                    custom_attrs[key] = serialize_custom_value(value) if value is not None else ''
            
            asset.custom_attrs = custom_attrs
            asset.save()
            messages.success(request, f'Asset "{asset.name}" updated successfully!')
            return redirect('asset_detail', pk=asset.pk)
    else:
        form = DynamicForm(instance=asset)
        form.fields['category'].queryset = AssetCategory.objects.filter(company=request.user.profile.company)    
    categories = AssetCategory.objects.filter(company=request.user.profile.company)
    return render(request, 'asset_form.html', {'form': form, 'title': 'Update Asset', 'asset': asset, 'categories': categories})

@login_required
def asset_detail(request, pk):
    asset = get_object_or_404(Asset, pk=pk, company=request.user.profile.company)
    
    # Get custom field definitions to display
    custom_definitions = CustomFieldDefinition.objects.filter(is_active=True, company=request.user.profile.company)
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
    fields = CustomFieldDefinition.objects.filter(company=request.user.profile.company)
    return render(request, 'custom_fields_list.html', {'fields': fields})

@user_passes_test(lambda u: u.is_staff)
def custom_field_create(request):
    if request.method == 'POST':
        form = CustomFieldDefinitionForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)  # don't save yet
            # Assign company from the logged-in user's profile
            # This works for both staff and superuser (if they have a profile)
            if hasattr(request.user, 'profile') and request.user.profile.company:
                field.company = request.user.profile.company
            else:
                # Fallback: if user has no profile (should not happen), show error
                messages.error(request, 'User profile missing company. Contact admin.')
                return redirect('custom_field_list')
            field.save()
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


def bulk_import(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        company = request.user.profile.company
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            # Get custom field definitions for this company
            custom_fields = CustomFieldDefinition.objects.filter(company=company, is_active=True)
            custom_field_names = [cf.name for cf in custom_fields]
            
            # Required standard columns
            required_columns = ['Name', 'Serial Number']  # match export headers
            missing = [col for col in required_columns if col not in df.columns]
            if missing:
                messages.error(request, f'Missing required columns: {", ".join(missing)}')
                return redirect('asset_list')
            
            success_count = 0
            error_rows = []
            for idx, row in df.iterrows():
                try:
                    # Get or create asset by serial_number + company
                    serial = str(row['Serial Number'])
                    asset, created = Asset.objects.update_or_create(
                        serial_number=serial,
                        company=company,
                        defaults={
                            'name': row.get('Name', ''),
                            'manufacturer': row.get('Manufacturer', ''),
                            'model_number': row.get('Model Number', ''),
                            'status': dict(Asset.STATUS_CHOICES).get(row.get('Status', 'available'), 'available'),
                            'purchase_cost': row.get('Purchase Cost') if pd.notna(row.get('Purchase Cost')) else None,
                            'purchase_date': row.get('Purchase Date') if pd.notna(row.get('Purchase Date')) else None,
                            'warranty_expiry': row.get('Warranty Expiry') if pd.notna(row.get('Warranty Expiry')) else None,
                            'assigned_to_name': row.get('Assigned To', ''),
                            'assigned_date': row.get('Assigned Date') if pd.notna(row.get('Assigned Date')) else None,
                            'location': row.get('Location', ''),
                            'notes': row.get('Notes', ''),
                            'created_by': request.user,
                        }
                    )
                    # Handle category
                    if 'Category' in df.columns and pd.notna(row.get('Category')):
                        cat_name = row['Category']
                        cat, _ = AssetCategory.objects.get_or_create(name=cat_name, company=company)
                        asset.category = cat
                        asset.save()
                    
                    # Handle custom fields
                    custom_attrs = asset.custom_attrs or {}
                    for cf in custom_fields:
                        cf_name = cf.name
                        if cf_name in df.columns and pd.notna(row[cf_name]):
                            custom_attrs[cf_name] = row[cf_name]
                        elif cf_name in df.columns:
                            # Allow clearing by setting empty string
                            custom_attrs[cf_name] = ''
                    asset.custom_attrs = custom_attrs
                    asset.save()
                    
                    success_count += 1
                except Exception as e:
                    error_rows.append(f"Row {idx+2}: {str(e)}")
            
            if error_rows:
                messages.warning(request, f"Imported {success_count} assets. Errors: {', '.join(error_rows[:5])}")
            else:
                messages.success(request, f"Successfully imported {success_count} assets.")
        except Exception as e:
            messages.error(request, f"Error reading file: {str(e)}")
        return redirect('asset_list')
    
    return render(request, 'bulk_import.html')


def bulk_export(request):
    company = request.user.profile.company
    assets = Asset.objects.filter(company=company).select_related('category')
    
    # Get all active custom field definitions for this company
    custom_fields = CustomFieldDefinition.objects.filter(company=company, is_active=True)
    custom_field_names = [cf.name for cf in custom_fields]
    
    # Build DataFrame
    data = []
    for asset in assets:
        row = {
            'Name': asset.name,
            'Serial Number': asset.serial_number,
            'Category': asset.category.name if asset.category else '',
            'Status': asset.get_status_display(),
            'Manufacturer': asset.manufacturer,
            'Model Number': asset.model_number,
            'Purchase Date': asset.purchase_date,
            'Purchase Cost': asset.purchase_cost,
            'Warranty Expiry': asset.warranty_expiry,
            'Assigned To': asset.assigned_to_name,
            'Assigned Date': asset.assigned_date,
            'Location': asset.location,
            'Notes': asset.notes,
            'Created At': asset.created_at,
        }
        # Add custom fields (ensure all defined custom fields appear, even if empty)
        for cf_name in custom_field_names:
            row[cf_name] = asset.custom_attrs.get(cf_name, '')
        data.append(row)
    
    df = pd.DataFrame(data)
    export_format = request.GET.get('format', 'csv')
    if export_format == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="assets_export.xlsx"'
        df.to_excel(response, index=False)
    else:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="assets_export.csv"'
        df.to_csv(response, index=False)
    return response


def download_template(request):
    company = request.user.profile.company
    # Get all custom fields for this company
    custom_fields = CustomFieldDefinition.objects.filter(company=company, is_active=True)
    
    # Define standard columns (matching export headers)
    standard_columns = [
        'Name', 'Serial Number', 'Category', 'Status', 'Manufacturer', 'Model Number',
        'Purchase Date', 'Purchase Cost', 'Warranty Expiry', 'Assigned To', 'Assigned Date',
        'Location', 'Notes'
    ]
    # Add custom field names as columns
    all_columns = standard_columns + [cf.name for cf in custom_fields]
    
    # Create a DataFrame with just headers (no data rows) or one example row
    # Option: add one example row to show format
    example_row = {col: '' for col in all_columns}
    example_row['Name'] = 'Example Laptop'
    example_row['Serial Number'] = 'SN123456'
    example_row['Status'] = 'available'
    # ... you can add more example values as needed
    df = pd.DataFrame([example_row])  # one row with example
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="import_template.xlsx"'
    df.to_excel(response, index=False)
    return response



def custom_report_export(request):
    company = request.user.profile.company
    selected_fields = request.GET.getlist('fields')
    if not selected_fields:
        messages.error(request, 'Please select at least one field.')
        return redirect('asset_list')
    
    # Get current filters from asset list (passed as hidden inputs)
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    
    # Additional report filters
    report_status = request.GET.get('report_status')
    report_category = request.GET.get('report_category')
    date_range = request.GET.get('date_range')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset for user's company
    qs = Asset.objects.filter(company=company)
    
    # Apply asset list filters
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(serial_number__icontains=search) |
            Q(manufacturer__icontains=search) |
            Q(model_number__icontains=search)
        )
    if category_filter:
        qs = qs.filter(category_id=category_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)
    
    # Apply report overrides
    if report_status:
        qs = qs.filter(status=report_status)
    if report_category:
        qs = qs.filter(category_id=report_category)
    
    # Apply date range
    today = datetime.now().date()
    if date_range == 'today':
        qs = qs.filter(created_at__date=today)
    elif date_range == 'week':
        week_ago = today - timedelta(days=7)
        qs = qs.filter(created_at__date__gte=week_ago)
    elif date_range == 'month':
        qs = qs.filter(created_at__year=today.year, created_at__month=today.month)
    elif date_range == 'custom' and date_from and date_to:
        qs = qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    
    # Build data rows
    data = []
    for asset in qs.select_related('category'):
        row = {}
        for field in selected_fields:
            if field.startswith('custom_'):
                key = field.replace('custom_', '')
                row[field] = asset.custom_attrs.get(key, '')
            elif field == 'category__name':
                row[field] = asset.category.name if asset.category else ''
            elif field == 'status':
                row[field] = asset.get_status_display()
            else:
                row[field] = getattr(asset, field, '')
        data.append(row)
    
    if not data:
        messages.warning(request, 'No data found for the selected criteria.')
        return redirect('asset_list')
    
    df = pd.DataFrame(data)
    format_type = request.GET.get('format', 'csv')
    
    if format_type == 'xlsx':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="custom_report.xlsx"'
        df.to_excel(response, index=False)
    else:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="custom_report.csv"'
        df.to_csv(response, index=False)
    return response


@login_required
def category_list(request):
    company = request.user.profile.company
    categories = AssetCategory.objects.filter(company=company).annotate(
        asset_count=Count('assets', filter=Q(assets__company=company))
    )
    # If you want to exclude retired assets from count:
    # from django.db.models import Q
    # categories = AssetCategory.objects.filter(company=company).annotate(
    #     asset_count=Count('assets', filter=Q(assets__company=company) & ~Q(assets__status='retired'))
    # )
    return render(request, 'category_list.html', {'categories': categories})

@login_required
def category_create(request):
    company = request.user.profile.company
    if request.method == 'POST':
        form = AssetCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.company = company
            category.save()
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('category_list')
    else:
        form = AssetCategoryForm()
    return render(request, 'category_form.html', {'form': form, 'title': 'Create Category'})

@login_required
def category_update(request, pk):
    company = request.user.profile.company
    category = get_object_or_404(AssetCategory, pk=pk, company=company)
    if request.method == 'POST':
        form = AssetCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('category_list')
    else:
        form = AssetCategoryForm(instance=category)
    return render(request, 'category_form.html', {'form': form, 'title': 'Edit Category'})

@login_required
def category_delete(request, pk):
    company = request.user.profile.company
    category = get_object_or_404(AssetCategory, pk=pk, company=company)
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully.')
        return redirect('category_list')
    return render(request, 'category_confirm_delete.html', {'category': category})



@login_required
def report_fault(request, asset_pk):
    asset = get_object_or_404(Asset, pk=asset_pk, company=request.user.profile.company)
    if request.method == 'POST':
        form = FaultReportForm(request.POST)
        if form.is_valid():
            fault = form.save(commit=False)
            fault.asset = asset
            fault.reported_by = request.user
            fault.save()
            # Update asset status to faulty
            asset.status = 'faulty'
            asset.save()
            messages.success(request, f'Fault reported for {asset.name}.')
            return redirect('asset_detail', pk=asset.pk)
    else:
        form = FaultReportForm()
    return render(request, 'report_fault.html', {'form': form, 'asset': asset})

@login_required
def resolve_fault(request, fault_pk):
    fault = get_object_or_404(FaultRecord, pk=fault_pk, asset__company=request.user.profile.company)
    if request.method == 'POST':
        fault.is_resolved = True
        fault.repaired_date = timezone.now()
        fault.repaired_by = request.user
        fault.repair_notes = request.POST.get('repair_notes', '')
        fault.repair_cost = request.POST.get('repair_cost') or None
        fault.save()
        # If no other unresolved faults, set asset status back to available
        if not fault.asset.fault_records.filter(is_resolved=False).exists():
            fault.asset.status = 'available'
            fault.asset.save()
        messages.success(request, f'Fault for {fault.asset.name} marked as resolved.')
        return redirect('asset_detail', pk=fault.asset.pk)
    return render(request, 'resolve_fault.html', {'fault': fault})




class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'registration/password_change.html'
    success_url = reverse_lazy('password_change')
    
    def form_valid(self, form):
        # Add success message
        messages.success(self.request, 'Your password has been changed successfully.')
        return super().form_valid(form)