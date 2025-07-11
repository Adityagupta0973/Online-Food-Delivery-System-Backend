import os 
from django.shortcuts import render
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from twilio.rest import Client

from FromOurKitchen.models import Cart, User, Address, ActiveOrders, MobileNumber
from FromOurKitchen.api.serializers import AddressSerializer, UserSerializer, ActiveOrdersSerializer

from Categories.models import Category, FoodItem, Stripe
from Categories.api.serializers import CategorySerializer, FoodItemSerializer

import stripe 

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        
        if user.groups.filter(name="category").exists():
            token['group'] = "category"
        else:
            token['group'] = "None"
        # ...

        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

@api_view(['POST'])
def customLogin(request):
    number = request.data['number']
    print('CUSTOM LOGIN')
    # Custom user authentication 
    
    try: 
        getUserID = MobileNumber.objects.get(number=number).user.id
        user = User.objects.get(id=getUserID)
    except ObjectDoesNotExist:
        return Response({'No user exists with that number ⚠️'}, status=status.HTTP_406_NOT_ACCEPTABLE)

    refresh = RefreshToken.for_user(user)

    # Add custom claims
    refresh['username'] = user.username
    
    if user.groups.filter(name="category").exists():
        refresh['group'] = "category"
    else:
        refresh['group'] = "None"
    # ...

    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    })
    

# User registration logic
@api_view(['GET', 'POST'])
def register(request):
    username = request.data["username"]
    email = request.data["email"]
    number = request.data["number"]

    # Ensure password matches confirmation
    password = request.data["password"]
    confirmation = request.data["confirmPassword"]
    if password != confirmation:
        return Response("ERROR: Passwords don't match", status=status.HTTP_406_NOT_ACCEPTABLE)
    
    # Input validation. Check if all data is provided
    if not email or not username or not password or not confirmation:
        return Response('All data is required', status=status.HTTP_406_NOT_ACCEPTABLE)


    # Attempt to create new user
    try:
        user = User.objects.create_user(username, email, password)
        mobile = MobileNumber(user=user, number=number)
        user.save()
        mobile.save()
    except IntegrityError:
        return Response("ERROR: Username/Number already taken", status=status.HTTP_406_NOT_ACCEPTABLE)
    return Response('Registered Successfully from backend')


# Refer: https://www.twilio.com/docs/verify/api?code-sample=code-step-2-send-a-verification-token&code-language=Python&code-sdk-version=7.x
# To send a text message with verification code to the requested mobile
@api_view(['POST'])
def mobileSendMessage(request):
    
    mobileNumber = request.data.get('number')  # Use .get() to avoid KeyError
    
    if not mobileNumber:  
        return Response({'error': 'Mobile number is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Find your Account SID and Auth Token at https://twilio.com/console
    # and set the environment variables. See http://twil.io/secure
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    try:
        verification = client.verify \
                            .services('VA24bec30d6e651140847153a21208a2f6') \
                            .verifications \
                            .create(to='+' + mobileNumber, channel='sms')

        print(verification.status)
        return Response({'Message Sent ✅'})

    except Exception as exception:
        # Check twilio's error code from here: https://www.twilio.com/docs/verify/api/v1/error-codes
        if exception.code == 60200:
            return Response({'Invalid Phone Number'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        elif exception.code == 60203:
            return Response({'Max attempts reached. Try sending message after some time ⚠️'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        else:
            return Response({'An unknown error occurred while sending message 🔴'}, status=status.HTTP_429_TOO_MANY_REQUESTS)


# Refer: https://www.twilio.com/docs/verify/api?code-sample=code-step-3-check-the-verification-token&code-language=Python&code-sdk-version=7.x
# To verify the verification code sent by Twilio to the user's mobile
@api_view(['POST'])
def mobileVerification(request):    
    mobileNumber = request.data['number']
    verificationCode = request.data['code']

    # Find your Account SID and Auth Token at https://twilio.com/console
    # and set the environment variables. See http://twil.io/secure
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    try:
        verification_check = client.verify \
                                .services('VA24bec30d6e651140847153a21208a2f6') \
                                .verification_checks \
                                .create(to= '+' + mobileNumber , code= verificationCode )

        if verification_check.status == 'approved':
            return Response({'Phone number verified ✅'})
        elif verification_check.status == 'pending':
            return Response({'Invalid verification code ⚠️'}, status=status.HTTP_412_PRECONDITION_FAILED)
        else:
            return Response({verification_check}, status=status.HTTP_406_NOT_ACCEPTABLE)


    except Exception as exception:
        # Check Twilio's error codes from here: https://www.twilio.com/docs/verify/api/v1/error-codes
        if exception.code == 60202:
            return Response({'Max verification attempt reached. Try after some time ⚠️'})
        else:
            return Response({'An unknown error occurred while verifying code 🔴'}, status=status.HTTP_429_TOO_MANY_REQUESTS)


# To view all the available/registered categories
@api_view(['GET'])
def category(request):
    # Uses the category model from the 'Categories' app
    categories = Category.objects.all()
    # Serialize the data for sending to frontend
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)
    

# To get the food items of the requested category. (food items added by that category)
@api_view(['GET'])
def categoriesFood(request, id):
    try:
        # Get the requested category
        category = Category.objects.get(id=id)
        # Get the food items of the above category
        categoriesFood = FoodItem.objects.filter(category = category)
    except :
        return Response('Not found', status=status.HTTP_404_NOT_FOUND)
    
    serializer = FoodItemSerializer(categoriesFood, many=True)
    return Response(serializer.data)


# To get the info of the requested category
@api_view(['GET'])
def categoryInfo(request, id):
    try:
        # Get the requested category
        category = Category.objects.filter(id=id)
    except KeyError:
        return Response('Not found', status=status.HTTP_404_NOT_FOUND)

    serializer = CategorySerializer(category, many=True)
    return Response(serializer.data)


# To get the items in the cart of the requested user
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getCartItems(request):    
    cart = Cart.objects.filter(user=request.user)
    # Custom serializer function is used for serializing the data. Refer to the Cart Model for more info about the serializer
    return Response([cart.serializer() for cart in cart])
    

# To add a food item to cart
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addToCart(request, id):
    # Add the food item to the user's cart
    try:
        # Get the requested foodItem
        food = FoodItem.objects.get(id=id)

        # For adding the item to cart

        # If the user's cart contains the requested food item, then increase it's quantity by 1
        try:
            getFood =  Cart.objects.get(food=food, user=request.user)
            getFood.qty += 1
            # Update the amount of the food item added in cart in accordance of it's quantity
            getFood.amount = float(food.price * getFood.qty)
            getFood.save()
        # If the cart doesn't contain the food, then add it to cart and set quantity to 1
        except ObjectDoesNotExist :
            addItem = Cart(user=request.user, food=food, qty=1, amount=food.price)
            addItem.save()
            
        # Update the cart's totalAmount by adding the current food item's price
        oldTotalAmount = Cart.objects.filter(user=request.user).first().totalAmount
        Cart.objects.filter(user=request.user).update(totalAmount = float(oldTotalAmount+food.price))
        

        # Get the added cart item of the requested user (for passing to serializer)
        cart = Cart.objects.get(user=request.user, food=id)
    
    # If a request is made with an invalid food ID, i.e food item doesn't exist, then return error
    except KeyError:
        return Response('Not found', status=status.HTTP_404_NOT_FOUND)
    
    # Serialize the cart for sending to frontend in appropriate format
    return Response(cart.serializer())
    

# To remove a food item from cart
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def removeFromCart(request, id):
    # Remove the food item from the user's cart
    try:
        # Get the requested foodItem
        food = FoodItem.objects.get(id=id)
        # If the user's cart contains the requested food item, then decrease it's quantity by 1
        try:
            getFood =  Cart.objects.get(food=food, user=request.user)
            # If the item's quantity is more than 1, then decrease it's quantity
            if getFood.qty > 1:
                getFood.qty -= 1
                # Update the amount of the food items removed from cart in accordance with its quantity
                getFood.amount = food.price * getFood.qty
                getFood.save()
            # If the item's quantity is 1 i.e the last item, then delete the item
            elif getFood.qty == 1:
                getFood.delete()
            # Else throw an error if qty is less than 1
            else :
                # If food qty is already 0, then return
                return Response('Food already removed from cart', status=status.HTTP_406_NOT_ACCEPTABLE)
                

        # If the cart doesn't contain the food, then return
        except ObjectDoesNotExist :
            return Response('Food is not present in the cart', status=status.HTTP_404_NOT_FOUND)
        try:
            # Update the cart's totalAmount by subtracting the current food item's price
            oldTotalAmount = Cart.objects.filter(user=request.user).first().totalAmount
            Cart.objects.filter(user=request.user).update(totalAmount = float(oldTotalAmount-food.price))
        except AttributeError:
            pass    

    # If a request is made with an invalid food ID, i.e food item doesn't exist, then return error
    except KeyError:
        return Response('Not found', status=status.HTTP_404_NOT_FOUND)
    
    return Response('Removed from cart')


# To add an address of a user
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addAddress(request):
    area = request.data['area']
    label = request.data['label']

    addAddress = Address(user=request.user, area=area, label=label)
    addAddress.save()

    return Response({'Address Added'})


# To get all the added address of a user
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getAddress(request):

    address = Address.objects.filter(user=request.user)
    serializer = AddressSerializer(address, many=True)

    
    return Response(serializer.data)



# To place an order of a customer with the requested data
# Creates a Stripe checkout session and returns back a URL to redirect to.
# Refer: https://stripe.com/docs/connect/enable-payment-acceptance-guide?platform=web#web-create-checkout for more information.
@api_view(['POST'])
@permission_classes([IsAuthenticated])  
def checkout(request):

    stripe.api_key = 'sk_test_51QmXiwGxJCMHsai04rgrfwstnIM16SB5jS2oTor9UFRbOWy0skksq0mVoRNgWItynzq3Bb3cGaP46Xq9v2hWgAUA004e6WwLXJ'
    
    # Get the cart items of the user
    cart = Cart.objects.filter(user=request.user)
    # Get the chosen delivery address passed from the frontend
    addressID = request.data['address'].get('id')

    # Get the category, from which the user wishes to buy food from
    getCartFoodID = cart.first().food.id
    getCategory = FoodItem.objects.get(id=getCartFoodID).category
    # Get the associated stripe account ID of the category. (Stored when category signed up with Stripe)
    accountID = Stripe.objects.get(category=getCategory).accountID
    
    line_items = []
    for item in cart:
        # Create a price object for each food item in the cart
        price_data = {
            'currency': 'inr',  # Ensure currency is correct as per your needs
            'unit_amount': int(item.food.price * 100),  # Convert price to cents (as Stripe expects amounts in cents)
            'product_data': {
                'name': item.food.name,
                'description': item.food.description,
            },
        }
        
        line_items.append({
            'price_data': price_data,
            'quantity': item.qty,
        })

    # To create a stripe checkout session which returns back the checkout session url
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            currency='inr',
            success_url= 'https://online-food-delivery-system.vercel.app/my-account',
            cancel_url= 'https://online-food-delivery-system.vercel.app/checkout/cancel',
            # Passes the metadata to a successfull checkout session by stripe if checkout is completed.
            # The metadata will be used to save order details
            metadata = {
                "user" : str(request.user.id),
                "addressID" : str(addressID), 
            }, 
            payment_intent_data={
                'transfer_data':{
                    'destination':'acct_1QnQVMGdffKEtkPL',
                }
            },
            stripe_account = 'acct_1QmXiwGxJCMHsai0',
        )
         
    except Exception as e:
        print('ERROR: ', e)
        return Response({'This category has not setup payment acceptance with Stripe yet !'}, status=status.HTTP_412_PRECONDITION_FAILED)

    return Response({session.url}, status=status.HTTP_303_SEE_OTHER)




# Stripe webhook to check if the payment is completed
# If payment is successfully completed, then save the order details
@api_view(['POST'])
def webhook_received(request):

    stripe.api_key = os.getenv('STRIPE_API_KEY')
    endpoint_secret = os.getenv('endpoint_secret') 

    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    print("Received payload:", payload)  # Debugging
    print("Received signature:", sig_header)  # Debugging

    if not sig_header:
        return HttpResponse({"error": "Missing Stripe-Signature header"}, status=400)
    
    # Verify webhook signature and extract the event.
    # See https://stripe.com/docs/webhooks/signatures for more information.
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload.
        print("Error: Invalid payload")  # Debugging
        return HttpResponse({"error": "Invalid signature"},status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid Signature.
        print("Error: Invalid signature")  # Debugging
        return HttpResponse({"error": "Invalid signature"},status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        payment_intent_id = session['payment_intent']
        # Fetch the PaymentIntent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        # Get the destination connected account from transfer_data
        connected_account_id = payment_intent['transfer_data']['destination']
        handle_completed_checkout_session(connected_account_id, session, request)

    else:
        print('Unhandled event type {}'.format(event['type']))
        
    return HttpResponse(status=200)




# If the checkout is completed, then call this function
def handle_completed_checkout_session(connected_account_id, session, request):
    # Fulfill the purchase.
    print('Connected account ID: ' + connected_account_id)
    print('PAYMENT COMPLETED ✅', str(session))
    
    # ---- Save the order details ----

    # Get the cart items of the user
    sessionUser = User.objects.get(id = session.metadata.user)
    cart = Cart.objects.filter(user=sessionUser)
    # Get the chosen delivery address passed from the frontend
    addressID = session.metadata.addressID
    address = Address.objects.get(id=addressID)
    # Save the details in active orders model
    addOrder = ActiveOrders(user=sessionUser, address=address)
    addOrder.save()
    # Add the user's cart's foodItems to the active order which user has placed
    for cartItem in cart:
        addOrder.cart.add(cartItem)

    print('Saved order details ✅')
    

    # ------- To send the user a text SMS using Twilio informing about their successfull order placement -----
    if os.getenv('TWILIO_ENABLED', 'False') == 'True':
        number = MobileNumber.objects.get(user=sessionUser).number

        # Find your Account SID and Auth Token at twilio.com/console
        # and set the environment variables. See http://twil.io/secure
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        client = Client(account_sid, auth_token)

        message = client.messages \
                        .create(
                            messaging_service_sid='MGf50dd0f886cfaa39b05a96200c338c37',
                            to='+' + str(number),
                            body="From Our Kitchen: Order Placed (" + str(cart.count()) + " item(s), Rs." + str(cart.first().totalAmount) +").\nHappy Eating!"
                        )

        print('Message sent ✅:', message.status)
    else:
        print("🔕 Twilio messaging is currently disabled (TWILIO_ENABLED is False)")


# To get the active orders of the logged in user
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getOrders(request):
    try:
        orders = ActiveOrders.objects.filter(user=request.user).order_by('-id')  # Adjust the filter based on your model
        serializer = ActiveOrdersSerializer(orders, many=True)
        return Response(serializer.data)
    except Exception as e:
        print("Error:", e)
        return Response({"error": "Internal server error"}, status=500)


# To get the info of the logged in user like name, email etc.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserInfo(request):

    serializer = UserSerializer(request.user)
    return Response(serializer.data)





# -------For DRF view --------------
@api_view(['GET'])
def getRoutes(request):
    routes = [
        '/api/token/',
        '/api/token/refresh/',
        '/api/mobile-send-message/',
        '/api/mobile-verification/',
        '/api/category/',
        '/api/category/<int:id>/',
        '/api/category/info/<int:id>/',
        '/api/get-cart-items/',
        '/api/add-to-cart/<int:id>/',
        '/api/remove-from-cart/<int:id>/',
        '/api/add-address/',
        '/api/get-address/',
        '/api/checkout/',
        '/api/webhook/',
        '/api/get-orders/',
        '/api/get-user-info/',
        '/api/custom-login/',
    ]

    return Response(routes)