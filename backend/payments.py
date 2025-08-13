import os
from typing import Dict, Any, Callable

import stripe
from flask import request, jsonify
from functools import wraps

# Initialize Stripe with secret key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# Simple in-memory store of active subscriptions keyed by customer ID
_active_subscriptions: Dict[str, bool] = {}


def create_plan(amount: int, nickname: str, currency: str = "usd", interval: str = "month") -> stripe.Price:
    """Create a subscription plan/price in Stripe."""
    return stripe.Price.create(
        unit_amount=amount,
        currency=currency,
        recurring={"interval": interval},
        product_data={"name": nickname},
    )


def create_subscription(customer_id: str, price_id: str) -> stripe.Subscription:
    """Subscribe a customer to a price."""
    sub = stripe.Subscription.create(customer=customer_id, items=[{"price": price_id}])
    _active_subscriptions[customer_id] = sub.get("status") == "active"
    return sub


def create_invoice(customer_id: str, amount: int, currency: str = "usd") -> stripe.Invoice:
    """Create and finalize an invoice for a customer."""
    stripe.InvoiceItem.create(customer=customer_id, amount=amount, currency=currency)
    invoice = stripe.Invoice.create(customer=customer_id, auto_advance=True)
    return invoice


def handle_webhook(payload: bytes, sig_header: str) -> Any:
    """Process incoming Stripe webhook events."""
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    event = stripe.Webhook.construct_event(payload, sig_header, secret)

    etype = event.get("type")
    data = event.get("data", {}).get("object", {})
    customer_id = data.get("customer")

    if etype in {"invoice.paid", "customer.subscription.created", "customer.subscription.updated"}:
        if customer_id:
            _active_subscriptions[customer_id] = True
    elif etype in {"customer.subscription.deleted", "invoice.payment_failed"}:
        if customer_id:
            _active_subscriptions[customer_id] = False

    return event


def has_active_subscription(customer_id: str) -> bool:
    """Check whether the customer has an active subscription."""
    return _active_subscriptions.get(customer_id, False)


def subscription_required(func: Callable) -> Callable:
    """Flask decorator to require an active subscription."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        customer_id = request.headers.get("X-Customer-ID", "")
        if not customer_id or not has_active_subscription(customer_id):
            return jsonify({"error": "Active subscription required"}), 402
        return func(*args, **kwargs)

    return wrapper

