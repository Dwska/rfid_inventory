from django.urls import path
from . import views

urlpatterns = [
    path('login/',                       views.rfid_login,        name='rfid_login'),
    path('logout/',                      views.rfid_logout,       name='rfid_logout'),
    path('dashboard/',                   views.dashboard,         name='dashboard'),
    path('inventory/',                   views.inventory_list,    name='inventory_list'),
    path('inventory/<int:pk>/',          views.product_detail,    name='product_detail'),
    path('cart/',                        views.cart_view,         name='cart'),
    path('checkout/',                    views.checkout,          name='checkout'),
    path('checkout/<int:pk>/confirm/',   views.checkout_confirm,  name='checkout_confirm'),
    path('log/',                         views.transaction_log,   name='transaction_log'),
    path('access-log/',                  views.access_log,        name='access_log'),
]