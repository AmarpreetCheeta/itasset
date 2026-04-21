from django import forms
from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Asset, AssetCategory, CustomFieldDefinition

# Update: 20 April 2026
class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    company_id = forms.CharField(max_length=50, required=True, help_text="Your company's unique ID", widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'company_id', 'password1', 'password2')


# New: 20 April 2026:
class CompanyLoginForm(AuthenticationForm):
    company_id = forms.CharField(max_length=50, label="Company ID", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Company ID'}))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username or Email'})
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})


class AssetBaseForm(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'name', 'serial_number', 'category', 'status', 'manufacturer',
            'model_number', 'purchase_date', 'purchase_cost', 'warranty_expiry',
            'assigned_to_name', 'assigned_date', 'location', 'notes'
        ]
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'warranty_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'assigned_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ['purchase_date', 'warranty_expiry', 'assigned_date']:
                self.fields[field].widget.attrs['class'] = 'form-control'
        
        self.fields['assigned_to_name'].widget.attrs['class'] = 'form-control'

def create_dynamic_asset_form(instance=None, category=None):
    """Create a form with dynamic custom fields based on definitions"""
    
    class DynamicAssetForm(AssetBaseForm):
        pass
    
    # Get active custom field definitions
    definitions = CustomFieldDefinition.objects.filter(is_active=True)
    if category:
        definitions = definitions.filter(models.Q(category=category) | models.Q(category__isnull=True))
    
    for definition in definitions:
        field_name = f"custom_{definition.name}"
        field_kwargs = {
            'label': definition.label,
            'required': definition.is_required,
            'help_text': definition.help_text,
        }
        
        # if definition.placeholder:
        #     field_kwargs['widget'] = forms.TextInput(attrs={'placeholder': definition.placeholder, 'class': 'form-control'})
        
        # Set initial value if instance exists
        # if instance and instance.custom_attrs.get(definition.name):
        #     field_kwargs['initial'] = instance.custom_attrs.get(definition.name)
        if instance:
            field_kwargs['initial'] = instance.custom_attrs.get(definition.name, '')
        
        # Create field based on type
        if definition.field_type == 'text':
            field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
            field_class = forms.CharField
        elif definition.field_type == 'number':
            field_kwargs['widget'] = forms.NumberInput(attrs={'class': 'form-control'})
            field_class = forms.DecimalField
        elif definition.field_type == 'date':
            field_kwargs['widget'] = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
            field_class = forms.DateField
        elif definition.field_type == 'boolean':
            field_kwargs['widget'] = forms.CheckboxInput(attrs={'class': 'form-check-input'})
            field_kwargs['required'] = False
            field_class = forms.BooleanField
        elif definition.field_type == 'email':
            field_kwargs['widget'] = forms.EmailInput(attrs={'class': 'form-control'})
            field_class = forms.EmailField
        elif definition.field_type == 'url':
            field_kwargs['widget'] = forms.URLInput(attrs={'class': 'form-control'})
            field_class = forms.URLField
        elif definition.field_type == 'textarea':
            field_kwargs['widget'] = forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
            field_class = forms.CharField
        elif definition.field_type == 'select' and definition.choices:
            choices = [(choice[0], choice[1]) for choice in definition.choices]
            field_kwargs['widget'] = forms.Select(attrs={'class': 'form-select'})
            field_kwargs['choices'] = choices
            field_class = forms.ChoiceField
        else:
            field_class = forms.CharField
            field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
        
        DynamicAssetForm.base_fields[field_name] = field_class(**field_kwargs)
    
    return DynamicAssetForm

class CustomFieldDefinitionForm(forms.ModelForm):
    class Meta:
        model = CustomFieldDefinition
        fields = ['name', 'label', 'field_type', 'choices', 'is_required', 'placeholder', 'help_text', 'category', 'order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-select'}),
            'choices': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Format: [["value1", "Label 1"], ["value2", "Label 2"]]'}),
            'placeholder': forms.TextInput(attrs={'class': 'form-control'}),
            'help_text': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }