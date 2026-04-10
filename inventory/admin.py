from django.contrib import admin
from .models import RFIDUser, Category, Product, Transaction, TransactionItem


@admin.register(RFIDUser)
class RFIDUserAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'rfid_code', 'role', 'department', 'is_active']
    list_filter = ['role', 'is_active', 'department']
    search_fields = ['full_name', 'rfid_code']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'stock', 'max_stock', 'location', 'stock_status']
    list_filter = ['category']
    search_fields = ['name', 'location']
    readonly_fields = ['stock_percentage', 'stock_status']


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    extra = 0
    readonly_fields = ['product_name_snapshot']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['rfid_user', 'checked_out_at']
    list_filter = ['checked_out_at']
    inlines = [TransactionItemInline]