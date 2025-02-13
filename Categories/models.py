from django.db import models
from django.contrib.auth.models import User


# Food Category details model
class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="category")
    name = models.CharField(max_length=64) 
    image = models.ImageField(upload_to='images/')

    def __str__(self):
        return f"{self.user} : {self.name}"


# Stripe model to store the stripe account ID of respective category
class Stripe(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='categoryStripe')
    accountID = models.CharField(max_length=32)

    def __str__(self):
        return f"{self.category}"


# Model for the food item.
class FoodItem(models.Model):
    # Refers to the Category Model (which category the food is associated with)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="categoryItem")
    name = models.CharField(max_length=32)
    description = models.CharField(max_length=320)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(upload_to='images/')

    def __str__(self):
        return f"{self.name}"

