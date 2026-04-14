from django.db import models
from django.utils import timezone


class RFIDUser(models.Model):
    ROLE_CHOICES = [
        ('technician', 'Technician'),
        ('supervisor', 'Supervisor'),
        ('engineer',   'Engineer'),
        ('admin',      'Admin'),
    ]

    full_name    = models.CharField(max_length=150)
    rfid_code    = models.CharField(max_length=50, unique=True, db_index=True)
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='technician')
    department   = models.CharField(max_length=100)
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    # Tracks last successful scan
    last_seen_at = models.DateTimeField(null=True, blank=True)
    login_count  = models.PositiveIntegerField(default=0)

    def record_login(self):
        """Call this every time a user successfully scans in."""
        self.last_seen_at = timezone.now()
        self.login_count += 1
        self.save(update_fields=['last_seen_at', 'login_count'])

    def __str__(self):
        return f"{self.full_name} ({self.rfid_code})"

    class Meta:
        verbose_name = "RFID User"
        ordering     = ['full_name']


class RFIDAccessLog(models.Model):
    """
    Records every scan attempt — successful or denied.
    Useful for security auditing.
    """
    RESULT_CHOICES = [
        ('granted', 'Access Granted'),
        ('denied',  'Access Denied'),
    ]

    rfid_code    = models.CharField(max_length=50)       # Raw code from scanner
    rfid_user    = models.ForeignKey(                    # Null if card not found
        RFIDUser,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='access_logs'
    )
    result       = models.CharField(max_length=10, choices=RESULT_CHOICES)
    scanned_at   = models.DateTimeField(auto_now_add=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    user_agent   = models.TextField(blank=True)

    def __str__(self):
        return f"{self.rfid_code} → {self.result} @ {self.scanned_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ['-scanned_at']
        verbose_name = "RFID Access Log"


class Category(models.Model):
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class Product(models.Model):
    name               = models.CharField(max_length=200)
    category           = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    description        = models.TextField(blank=True)
    location           = models.CharField(max_length=100)
    stock              = models.PositiveIntegerField(default=0)
    max_stock          = models.PositiveIntegerField(default=100)
    reorder_threshold  = models.PositiveIntegerField(default=10)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    @property
    def stock_percentage(self):
        if self.max_stock == 0:
            return 0
        return round((self.stock / self.max_stock) * 100)

    @property
    def stock_status(self):
        pct = self.stock_percentage
        if pct <= 15: return 'critical'
        if pct <= 35: return 'low'
        return 'ok'

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Transaction(models.Model):
    rfid_user       = models.ForeignKey(
        RFIDUser, on_delete=models.SET_NULL, null=True, related_name='transactions'
    )
    checked_out_at  = models.DateTimeField(default=timezone.now)
    notes           = models.TextField(blank=True)

    def __str__(self):
        return f"{self.rfid_user} @ {self.checked_out_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ['-checked_out_at']


class TransactionItem(models.Model):
    transaction           = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')
    product               = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity              = models.PositiveIntegerField()
    product_name_snapshot = models.CharField(max_length=200)

    def save(self, *args, **kwargs):
        if self.product and not self.product_name_snapshot:
            self.product_name_snapshot = self.product.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name_snapshot} x{self.quantity}"