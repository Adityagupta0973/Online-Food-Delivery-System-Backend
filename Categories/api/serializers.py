from rest_framework.serializers import ModelSerializer
from Categories.models import FoodItem, Category


# Creates JSON objects out of the Python objects
class FoodItemSerializer(ModelSerializer):
    class Meta:
        model = FoodItem
        fields = '__all__'


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
