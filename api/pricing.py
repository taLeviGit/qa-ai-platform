BASE_PRICE = 1000
CAR_VALUE_RATE = 0.02
DISCOUNT_AGE = 25
DISCOUNT_RATE = 0.10
SENIOR_AGE = 70
SENIOR_SURCHARGE = 0.20

def calculate_price(age: int , car_value: float) -> float:
    """
    Pricing rules (the requirement):
    - Base price: 1000 + 2% of the car value
    - Age 25 and above: 10% discount
    - Age 70 and above: 20% surcharge (instead of the discount)
    """
    
    price = BASE_PRICE + car_value * CAR_VALUE_RATE
    
    if age >= SENIOR_AGE:
        price *= 1 + SENIOR_SURCHARGE
    elif age > DISCOUNT_AGE:
        price *= 1 - DISCOUNT_RATE
    
    return round(price, 2)
    
