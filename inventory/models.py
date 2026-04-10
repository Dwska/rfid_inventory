from django.db import models
from django.utils import timezone


class RFIDUser(models.Model):
    """
    Represents a physical person with an RFID card.
    Not linked to Django's auth system — authentication
    happens via RFID card scan, not username/password.
    """
    ROLE_CHOICES = [
        ('technician', 'Technician'),
        ('supervisor', 'Supervisor'),
        ('engineer', 'Engineer'),
        ('admin', 'Admin'),
    ]

    full_name = models.CharField(max_length=150)
    rfid_code = models.CharField(max_length=50, unique=True)  # e.g. "RFID-A1B2"
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='technician')
    department = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.rfid_code})"

    class Meta:
        verbose_name = "RFID User"
        ordering = ['full_name']


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Product(models.Model):
    """
    An inventory item stored in the room.
    """
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=100, help_text="e.g. Rack A-1, Drawer B-3")
    stock = models.PositiveIntegerField(default=0)
    max_stock = models.PositiveIntegerField(default=100)
    reorder_threshold = models.PositiveIntegerField(
        default=10,
        help_text="Alert when stock falls below this number"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def stock_percentage(self):
        if self.max_stock == 0:
            return 0
        return round((self.stock / self.max_stock) * 100)

    @property
    def stock_status(self):
        pct = self.stock_percentage
        if pct <= 15:
            return 'critical'
        elif pct <= 35:
            return 'low'
        return 'ok'

    class Meta:
        ordering = ['name']


class Transaction(models.Model):
    """
    Records every checkout event — who took what, and when.
    """
    rfid_user = models.ForeignKey(
        RFIDUser, on_delete=models.SET_NULL, null=True, related_name='transactions'
    )
    checked_out_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.rfid_user} @ {self.checked_out_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-checked_out_at']


class TransactionItem(models.Model):
    """
    Each line item inside a transaction (one product + quantity).
    """
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    product_name_snapshot = models.CharField(max_length=200)  # Preserve name if product deleted

    def save(self, *args, **kwargs):
        if self.product and not self.product_name_snapshot:
            self.product_name_snapshot = self.product.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name_snapshot} x{self.quantity}"