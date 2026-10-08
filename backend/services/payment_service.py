"""
payment_service.py
------------------
Configuration point for a future online payment gateway (e.g. Razorpay).

No gateway is integrated yet, so `gateway_configured()` is False and checkout
offers only Cash on Delivery / Pay at Store (and manual UPI when a UPI ID is
set in Admin -> Settings). A payment is NEVER marked paid automatically;
the admin records it from the order page.

To add a gateway later:
  1. set PAYMENT_GATEWAY=<name> plus its keys in backend/.env
  2. implement create_payment() / verify_payment() for it below
  3. return True from gateway_configured() only when both are implemented
"""
import os

SUPPORTED_GATEWAYS = ()        # add the gateway name here once implemented


def gateway_name():
    return (os.getenv("PAYMENT_GATEWAY") or "").strip().lower()


def gateway_configured():
    return gateway_name() in SUPPORTED_GATEWAYS


def create_payment(order):                       # pragma: no cover - placeholder
    raise NotImplementedError("No online payment gateway is configured")


def verify_payment(order, payload):              # pragma: no cover - placeholder
    raise NotImplementedError("No online payment gateway is configured")
