from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction
from django.views.decorators.http import require_POST

from .models import RFIDUser, RFIDAccessLog, Product, Transaction, TransactionItem
from .forms  import RFIDLoginForm


# ── Helpers ────────────────────────────────────────────────────────────────

def get_rfid_user(request):
    uid = request.session.get('rfid_user_id')
    if not uid:
        return None
    try:
        return RFIDUser.objects.get(pk=uid, is_active=True)
    except RFIDUser.DoesNotExist:
        return None


def rfid_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not get_rfid_user(request):
            messages.warning(request, "Please scan your RFID card to access this page.")
            return redirect('rfid_login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def get_cart(request):
    return request.session.get('cart', {})


def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ── Authentication ─────────────────────────────────────────────────────────

def rfid_login(request):
    #─────────────Debug Input Form in Login──────────────────────────
    # if request.method == 'POST':
    #     print("RAW POST DATA:", request.POST)
    #     print("RAW rfid_code value:", repr(request.POST.get('rfid_code', '')))
    """
    Main RFID login view.

    GET  → show the login page (input always focused, waiting for card tap)
    POST → receive rfid_code from form, validate against PostgreSQL,
           grant or deny access, log the attempt either way.
    """
    if get_rfid_user(request):
        return redirect('dashboard')

    error   = None
    form    = RFIDLoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        rfid_code  = form.cleaned_data['rfid_code'].strip().upper()
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # ── Query PostgreSQL ───────────────────────────────────────────────
        try:
            rfid_user = RFIDUser.objects.get(rfid_code=rfid_code)

            if not rfid_user.is_active:
                # Card exists but access has been revoked
                RFIDAccessLog.objects.create(
                    rfid_code  = rfid_code,
                    rfid_user  = rfid_user,
                    result     = 'denied',
                    ip_address = ip_address,
                    user_agent = user_agent,
                )
                error = "Your access has been revoked. Contact your administrator."

            else:
                # ✅ ACCESS GRANTED
                RFIDAccessLog.objects.create(
                    rfid_code  = rfid_code,
                    rfid_user  = rfid_user,
                    result     = 'granted',
                    ip_address = ip_address,
                    user_agent = user_agent,
                )
                rfid_user.record_login()

                # Store user in session
                request.session['rfid_user_id']   = rfid_user.pk
                request.session['rfid_user_name'] = rfid_user.full_name
                request.session['cart']           = {}

                messages.success(request, f"Welcome, {rfid_user.full_name}!")
                return redirect('dashboard')

        except RFIDUser.DoesNotExist:
            # ❌ Card not found in database at all
            RFIDAccessLog.objects.create(
                rfid_code  = rfid_code,
                rfid_user  = None,          # Unknown card — no user linked
                result     = 'denied',
                ip_address = ip_address,
                user_agent = user_agent,
            )
            error = f"Card '{rfid_code}' is not registered. Access denied."

    else:
            # Show the actual validation errors instead of a generic message
            error = "Form error: " + " | ".join(
                f"{field}: {', '.join(errs)}"
                for field, errs in form.errors.items()
            )

    # On GET request, error is still None here — don't include it in context
    context = {'form': form}
    if error:                    # ← only add error key if it actually has content
        context['error'] = error

    return render(request, 'inventory/login.html', context)


def rfid_logout(request):
    request.session.flush()
    messages.info(request, "You have been signed out.")
    return redirect('rfid_login')


# ── Dashboard ──────────────────────────────────────────────────────────────

@rfid_required
def dashboard(request):
    rfid_user = get_rfid_user(request)
    products  = Product.objects.select_related('category').all()
    low_stock = [p for p in products if p.stock_status in ('low', 'critical')]
    cart      = get_cart(request)

    # Recent access logs for this user
    recent_logs = RFIDAccessLog.objects.filter(
        rfid_user=rfid_user
    ).order_by('-scanned_at')[:5]

    context = {
        'rfid_user':            rfid_user,
        'total_products':       products.count(),
        'low_stock_count':      len(low_stock),
        'cart_count':           sum(cart.values()),
        'low_stock_items':      low_stock[:5],
        'recent_transactions':  Transaction.objects.select_related('rfid_user').all()[:5],
        'recent_logs':          recent_logs,
    }
    return render(request, 'inventory/dashboard.html', context)


# ── Inventory ──────────────────────────────────────────────────────────────

@rfid_required
def inventory_list(request):
    rfid_user       = get_rfid_user(request)
    search          = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')

    products = Product.objects.select_related('category').all()
    if search:
        products = products.filter(name__icontains=search)
    if category_filter:
        products = products.filter(category__name__icontains=category_filter)

    cart = get_cart(request)
    return render(request, 'inventory/inventory_list.html', {
        'rfid_user':       rfid_user,
        'products':        products,
        'cart_count':      sum(cart.values()),
        'search':          search,
        'category_filter': category_filter,
    })


@rfid_required
def product_detail(request, pk):
    rfid_user = get_rfid_user(request)
    product   = get_object_or_404(Product, pk=pk)
    cart      = get_cart(request)

    if request.method == 'POST':
        qty             = int(request.POST.get('quantity', 1))
        already_in_cart = cart.get(str(pk), 0)
        if already_in_cart + qty > product.stock:
            messages.error(request, "Not enough stock available.")
        else:
            cart[str(pk)] = already_in_cart + qty
            save_cart(request, cart)
            messages.success(request, f"Added {qty}× {product.name} to cart.")
        return redirect('product_detail', pk=pk)

    return render(request, 'inventory/product_detail.html', {
        'rfid_user':  rfid_user,
        'product':    product,
        'cart_count': sum(cart.values()),
        'in_cart':    cart.get(str(pk), 0),
    })


# ── Cart & Checkout ────────────────────────────────────────────────────────

@rfid_required
def cart_view(request):
    rfid_user  = get_rfid_user(request)
    cart       = get_cart(request)
    cart_items = []

    for pid, qty in cart.items():
        try:
            p = Product.objects.get(pk=int(pid))
            cart_items.append({'product': p, 'qty': qty})
        except Product.DoesNotExist:
            pass

    if request.method == 'POST':
        action = request.POST.get('action')
        pid    = request.POST.get('product_id')
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

    return render(request, 'inventory/cart.html', {
        'rfid_user':  rfid_user,
        'cart_items': cart_items,
        'cart_count': sum(cart.values()),
    })


@rfid_required
def checkout(request):
    rfid_user  = get_rfid_user(request)
    cart       = get_cart(request)

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
                        transaction           = txn,
                        product               = product,
                        quantity              = qty,
                        product_name_snapshot = product.name,
                    )
            save_cart(request, {})
            messages.success(request, "Checkout successful!")
            return redirect('checkout_confirm', pk=txn.pk)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('cart')

    return render(request, 'inventory/checkout_confirm.html', {
        'rfid_user':  rfid_user,
        'cart_items': cart_items,
        'cart_count': sum(cart.values()),
    })


@rfid_required
def checkout_confirm(request, pk):
    rfid_user = get_rfid_user(request)
    txn       = get_object_or_404(Transaction, pk=pk)
    return render(request, 'inventory/checkout_success.html', {
        'rfid_user':   rfid_user,
        'transaction': txn,
        'cart_count':  0,
    })


@rfid_required
def transaction_log(request):
    rfid_user    = get_rfid_user(request)
    transactions = Transaction.objects.select_related('rfid_user').prefetch_related('items').all()
    return render(request, 'inventory/transaction_log.html', {
        'rfid_user':    rfid_user,
        'transactions': transactions,
        'cart_count':   sum(get_cart(request).values()),
    })


# ── Access Log (admin view) ────────────────────────────────────────────────

@rfid_required
def access_log(request):
    rfid_user = get_rfid_user(request)
    if rfid_user.role not in ('admin', 'supervisor'):
        messages.error(request, "You don't have permission to view this page.")
        return redirect('dashboard')

    logs = RFIDAccessLog.objects.select_related('rfid_user').all()[:100]
    return render(request, 'inventory/access_log.html', {
        'rfid_user':  rfid_user,
        'logs':       logs,
        'cart_count': sum(get_cart(request).values()),
    })