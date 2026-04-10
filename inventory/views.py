from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction
from .models import RFIDUser, Product, Transaction, TransactionItem
from .forms import RFIDLoginForm


# ── Helpers ────────────────────────────────────────────────────────────────

def get_rfid_user(request):
    """Pull the logged-in RFID user from the session."""
    uid = request.session.get('rfid_user_id')
    if not uid:
        return None
    try:
        return RFIDUser.objects.get(pk=uid, is_active=True)
    except RFIDUser.DoesNotExist:
        return None


def rfid_required(view_func):
    """Decorator: redirect to login if no RFID session."""
    def wrapper(request, *args, **kwargs):
        if not get_rfid_user(request):
            return redirect('rfid_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_cart(request):
    return request.session.get('cart', {})   # {product_id: quantity}


def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


# ── Views ──────────────────────────────────────────────────────────────────

def rfid_login(request):
    """
    Step 1 — RFID authentication.
    In production, your RFID reader POSTs the card code here automatically.
    The user just taps their card; no keyboard needed.
    """
    if get_rfid_user(request):
        return redirect('dashboard')

    form = RFIDLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        code = form.cleaned_data['rfid_code']
        user = RFIDUser.objects.get(rfid_code=code)
        request.session['rfid_user_id'] = user.pk
        request.session['cart'] = {}
        messages.success(request, f"Welcome, {user.full_name}!")
        return redirect('dashboard')

    return render(request, 'inventory/login.html', {'form': form})


def rfid_logout(request):
    request.session.flush()
    messages.info(request, "You have been signed out.")
    return redirect('rfid_login')


@rfid_required
def dashboard(request):
    rfid_user = get_rfid_user(request)
    products = Product.objects.select_related('category').all()
    low_stock = [p for p in products if p.stock_status in ('low', 'critical')]
    cart = get_cart(request)
    cart_count = sum(cart.values())

    context = {
        'rfid_user': rfid_user,
        'total_products': products.count(),
        'low_stock_count': len(low_stock),
        'cart_count': cart_count,
        'low_stock_items': low_stock[:5],
        'recent_transactions': Transaction.objects.select_related('rfid_user').all()[:5],
    }
    return render(request, 'inventory/dashboard.html', context)


@rfid_required
def inventory_list(request):
    rfid_user = get_rfid_user(request)
    category_filter = request.GET.get('category', '')
    search = request.GET.get('q', '')

    products = Product.objects.select_related('category').all()
    if category_filter:
        products = products.filter(category__name__icontains=category_filter)
    if search:
        products = products.filter(name__icontains=search)

    cart = get_cart(request)

    context = {
        'rfid_user': rfid_user,
        'products': products,
        'cart_count': sum(cart.values()),
        'search': search,
        'category_filter': category_filter,
    }
    return render(request, 'inventory/inventory_list.html', context)


@rfid_required
def product_detail(request, pk):
    rfid_user = get_rfid_user(request)
    product = get_object_or_404(Product, pk=pk)
    cart = get_cart(request)

    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 1))
        already_in_cart = cart.get(str(pk), 0)
        if already_in_cart + qty > product.stock:
            messages.error(request, "Not enough stock available.")
        else:
            cart[str(pk)] = already_in_cart + qty
            save_cart(request, cart)
            messages.success(request, f"Added {qty}× {product.name} to cart.")
        return redirect('product_detail', pk=pk)

    context = {
        'rfid_user': rfid_user,
        'product': product,
        'cart_count': sum(cart.values()),
        'in_cart': cart.get(str(pk), 0),
    }
    return render(request, 'inventory/product_detail.html', context)


@rfid_required
def cart_view(request):
    rfid_user = get_rfid_user(request)
    cart = get_cart(request)

    cart_items = []
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(pk=int(pid))
            cart_items.append({'product': p, 'qty': qty})
        except Product.DoesNotExist:
            pass

    if request.method == 'POST':
        action = request.POST.get('action')
        pid = request.POST.get('product_id')
        if action == 'remove' and pid in cart:
            del cart[pid]
            save_cart(request, cart)
        elif action == 'update' and pid in cart:
            new_qty = int(request.POST.get('quantity', 1))
            try:
                p = Product.objects.get(pk=int(pid))
                if 1 <= new_qty <= p.stock:
                    cart[pid] = new_qty
                    save_cart(request, cart)
            except Product.DoesNotExist:
                pass
        return redirect('cart')

    context = {
        'rfid_user': rfid_user,
        'cart_items': cart_items,
        'cart_count': sum(cart.values()),
    }
    return render(request, 'inventory/cart.html', context)


@rfid_required
def checkout(request):
    """
    Deduct all cart items from stock and record the transaction.
    Uses a DB transaction so it's atomic — either all succeeds or all rolls back.
    """
    rfid_user = get_rfid_user(request)
    cart = get_cart(request)

    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('cart')

    cart_items = []
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(pk=int(pid))
            cart_items.append((p, qty))
        except Product.DoesNotExist:
            pass

    if request.method == 'POST':
        try:
            with db_transaction.atomic():
                txn = Transaction.objects.create(rfid_user=rfid_user)
                for product, qty in cart_items:
                    if product.stock < qty:
                        raise ValueError(f"Insufficient stock for {product.name}")
                    product.stock -= qty
                    product.save()
                    TransactionItem.objects.create(
                        transaction=txn,
                        product=product,
                        quantity=qty,
                        product_name_snapshot=product.name,
                    )
            save_cart(request, {})
            messages.success(request, "Checkout successful!")
            return redirect('checkout_confirm', pk=txn.pk)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('cart')

    context = {
        'rfid_user': rfid_user,
        'cart_items': cart_items,
        'cart_count': sum(cart.values()),
    }
    return render(request, 'inventory/checkout_confirm.html', context)


@rfid_required
def checkout_confirm(request, pk):
    rfid_user = get_rfid_user(request)
    txn = get_object_or_404(Transaction, pk=pk)
    return render(request, 'inventory/checkout_success.html', {
        'rfid_user': rfid_user,
        'transaction': txn,
        'cart_count': 0,
    })


@rfid_required
def transaction_log(request):
    rfid_user = get_rfid_user(request)
    transactions = Transaction.objects.select_related('rfid_user').prefetch_related('items').all()
    return render(request, 'inventory/transaction_log.html', {
        'rfid_user': rfid_user,
        'transactions': transactions,
        'cart_count': sum(get_cart(request).values()),
    })