from django.contrib import admin

# Register your models here.
from .models import Category, FoodItem, Stripe

admin.site.register(Category)
admin.site.register(FoodItem)
admin.site.register(Stripe)