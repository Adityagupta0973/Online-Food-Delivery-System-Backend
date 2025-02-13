from rest_framework.serializers import ModelSerializer
from Categories.api.serializers import CategorySerializer, FoodItemSerializer
from FromOurKitchen.models import Cart, Address, User, ActiveOrders
from rest_framework import serializers

# Creates JSON objects out of the Python objects
class CartSerializer(ModelSerializer):
    food = FoodItemSerializer(read_only=True)
    class Meta:
        model = Cart
        fields = ['id', 'user', 'food', 'qty', 'amount', 'totalAmount']


class AddressSerializer(ModelSerializer):
    class Meta:
        model = Address 
        fields = '__all__'


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name']


class ActiveOrdersSerializer(ModelSerializer):
    cart = CartSerializer(read_only=True, many=True)
    address = AddressSerializer(read_only=True)
    
    class Meta:
        model = ActiveOrders
        fields = ['id', 'cart', 'address', 'date', 'time', 'active']
