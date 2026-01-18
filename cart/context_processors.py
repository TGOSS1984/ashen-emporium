from .cart import Cart

def cart_counts(request):
    cart = Cart(request.session)
    return {"cart_count": cart.count_items()}
