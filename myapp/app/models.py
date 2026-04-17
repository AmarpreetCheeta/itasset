from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone

class AssetCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='bi-laptop')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Asset Categories"

    def __str__(self):
        return self.name

class Asset(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired'),
        ('lost', 'Lost/Stolen'),
    ]

    name = models.CharField(max_length=200)
    serial_number = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True, related_name='assets')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    # Hardware/Software Details
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    
    # Financial Details
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    warranty_expiry = models.DateField(null=True, blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets')
    assigned_date = models.DateField(null=True, blank=True)
    
    # Additional Info
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Custom Fields Storage
    custom_attrs = models.JSONField(default=dict, blank=True)
    
    # Audit Fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_assets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    @property
    def is_warranty_expired(self):
        if self.warranty_expiry:
            return self.warranty_expiry < timezone.now().date()
        return False

class CustomFieldDefinition(models.Model):
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('boolean', 'Yes/No'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('textarea', 'Text Area'),
        ('select', 'Dropdown'),
    ]

    name = models.CharField(max_length=100, unique=True, help_text="Field identifier (used as key in JSON)")
    label = models.CharField(max_length=200, help_text="Display label")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    choices = models.JSONField(default=list, blank=True, help_text="For dropdown: list of [value, label] pairs")
    is_required = models.BooleanField(default=False)
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True, blank=True, 
                                  help_text="Leave blank for all categories")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.label