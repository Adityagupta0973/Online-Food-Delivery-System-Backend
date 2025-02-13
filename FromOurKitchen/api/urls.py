from django.urls import path
from . import views
from .views import MyTokenObtainPairView

# urlpatterns = [
#     path('', home) 
# ]

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

# Refer to the corresponding view function for more detials of the url routes
urlpatterns = [ 
    # To display a list of available API routes through DRF
    path('', views.getRoutes, name="index"),

    # User authentication
    path('register/', views.register, name="register" ),
    path('mobile-send-message/', views.mobileSendMessage, name="mobileSendMessage"),
    path('mobile-verification/', views.mobileVerification, name='mobileVerification'),

    # To get all the category, and their data (food, information)
    path('category/', views.category, name="category"),
    path('category/<int:id>', views.categoriesFood, name="categoriesFood"),
    path('category/info/<int:id>', views.categoryInfo, name="categoryInfo"),
    
    # To get, add or remove item(s) from user's cart
    path('get-cart-items/', views.getCartItems, name="getCartItems"),
    path('add-to-cart/<int:id>', views.addToCart, name="addToCart"),
    path('remove-from-cart/<int:id>', views.removeFromCart, name="removeFromCart"),

    # To add a user's address, and to get all the address added by the user
    path('add-address/', views.addAddress, name='addAddress'),
    path('get-address/', views.getAddress, name='getAddress'),

    # To place an order, to get a user's existing orders, and to get the logged in user's info
    path('checkout/', views.checkout, name='checkout'),
    path('webhook/', views.webhook_received, name='webhookReceived'), 
    path('get-orders/', views.getOrders, name='getOrders'),
    path('get-user-info/', views.getUserInfo, name='getUserInfo'),
 
    # For user authentication
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('custom-login/', views.customLogin, name='customLogin'),
]
