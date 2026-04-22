from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


# New Company model
class Company(models.Model):
    name = models.CharField(max_length=200, unique=True, null=True)
    company_id = models.CharField(max_length=50, unique=True, help_text="Unique identifier for login", null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name

# Add company ForeignKey to User (via OneToOne profile, but simpler: add field directly)
# Since we can't modify User directly easily, create a UserProfile
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users', null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.company.name}"
    

class AssetCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='bi-laptop')
    #New 20 April 2026:
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='categories', null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Asset Categories"
        #New 20 April 2026:
        unique_together = ['name', 'company']  # names unique per company

    def __str__(self):
        return self.name
    


class Asset(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('assigned', 'Assigned'),
        ('maintenance', 'Under Maintenance'),
        ('faulty', 'Faulty'),   # new
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
    # assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_assets') # Deleted
    assigned_to_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Assigned To") # New field instaed of assigned_to
    assigned_date = models.DateField(null=True, blank=True)
    
    # Additional Info
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    
    # Custom Fields Storage
    custom_attrs = models.JSONField(default=dict, blank=True)
    
    # Audit Fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_assets')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='assets', null=True)   # NEW: 20 April 2026
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['serial_number', 'company']   # serial number unique per company

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

    name = models.CharField(max_length=100, help_text="Field identifier (used as key in JSON)")
    label = models.CharField(max_length=200, help_text="Display label")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    choices = models.JSONField(default=list, blank=True, help_text="For dropdown: list of [value, label] pairs", null=True)
    is_required = models.BooleanField(default=False)
    placeholder = models.CharField(max_length=200, blank=True)
    help_text = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(AssetCategory, on_delete=models.SET_NULL, null=True, blank=True, 
                                  help_text="Leave blank for all categories")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='custom_fields', null=True)   # New: 20 April 2026
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['name', 'company'] # New: 20 April 2026
        ordering = ['order', 'name']

    def __str__(self):
        if self.company:
            return f"{self.label} ({self.company.name})"
        return f"{self.label} (No Company)"
    

class FaultRecord(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='fault_records')
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reported_faults')
    reported_date = models.DateTimeField(auto_now_add=True)
    fault_description = models.TextField()
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium')
    repair_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    repair_notes = models.TextField(blank=True)
    repaired_date = models.DateTimeField(null=True, blank=True)
    repaired_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='repaired_faults')
    is_resolved = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-reported_date']
    
    def __str__(self):
        return f"{self.asset.name} - {self.reported_date.strftime('%Y-%m-%d')}"