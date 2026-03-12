from __future__ import annotations

import os
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any

import stripe
from flask import Flask, request, jsonify


# =============================================================================
# Configuration
# =============================================================================

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

app = Flask(__name__)


# =============================================================================
# Domain model for local application state
# =============================================================================

class OrderStatus(str, Enum):
    CREATED = "created"
    PAYMENT_INTENT_CREATED = "payment_intent_created"
    REQUIRES_ACTION = "requires_action"
    AUTHORIZED = "authorized"
    APPROVED_FOR_CAPTURE = "approved_for_capture"
    CAPTURED = "captured"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    CANCELED = "canceled"
    FAILED = "failed"


@dataclass
class Order:
    order_id: str
    amount: int
    currency: str
    customer_email: str
    customer_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    payment_intent_id: Optional[str] = None
    latest_charge_id: Optional[str] = None
    amount_captured: int = 0
    amount_refunded: int = 0
    requires_review: bool = False
    approved_for_capture: bool = False
    status: OrderStatus = OrderStatus.CREATED
    history: list[dict[str, Any]] = field(default_factory=list)

    def log(self, action: str, **kwargs: Any) -> None:
        self.history.append({"action": action, **kwargs})


# In-memory store for demo purposes only.
ORDERS: Dict[str, Order] = {}
PROCESSED_WEBHOOK_EVENTS: set[str] = set()


# =============================================================================
# Helpers
# =============================================================================

def get_order(order_id: str) -> Order:
    if order_id not in ORDERS:
        raise KeyError(f"Unknown order_id={order_id}")
    return ORDERS[order_id]


def ensure_customer(email: str) -> stripe.Customer:
    """
    Naive lookup/create. In production, persist your Stripe customer IDs locally.
    """
    existing = stripe.Customer.list(email=email, limit=1)
    if existing.data:
        return existing.data[0]
    return stripe.Customer.create(email=email)


def persist_order(order: Order) -> None:
    ORDERS[order.order_id] = order


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


# =============================================================================
# Complex payment flow service
# =============================================================================

class StripePaymentFlow:
    """
    Complex flow:
    1. Create or find customer
    2. Attach/select payment method
    3. Create PaymentIntent with manual capture
    4. Confirm PaymentIntent
    5. Handle:
       - requires_action (3DS/SCA)
       - requires_capture (authorized, awaiting capture)
       - succeeded (rare here, but possible under different capture methods)
    6. Internal review/approval
    7. Capture partially or fully
    8. Refund partially or fully
    9. Process disputes via webhook
    """

    def create_order(
        self,
        order_id: str,
        amount: int,
        currency: str,
        customer_email: str,
        requires_review: bool = False,
    ) -> Order:
        require(amount > 0, "amount must be positive")
        require(currency.isalpha() and len(currency) == 3, "currency must be 3-letter ISO code")

        order = Order(
            order_id=order_id,
            amount=amount,
            currency=currency.lower(),
            customer_email=customer_email,
            requires_review=requires_review,
            status=OrderStatus.CREATED,
        )
        order.log("order_created", amount=amount, currency=currency.lower())
        persist_order(order)
        return order

    def attach_payment_method_to_customer(
        self,
        order_id: str,
        payment_method_id: str,
    ) -> Order:
        order = get_order(order_id)

        customer = ensure_customer(order.customer_email)
        order.customer_id = customer.id

        # Attach PM if not already attached.
        pm = stripe.PaymentMethod.retrieve(payment_method_id)
        if not getattr(pm, "customer", None):
            stripe.PaymentMethod.attach(payment_method_id, customer=customer.id)

        # Set default invoice PM for convenience; not strictly required.
        stripe.Customer.modify(
            customer.id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        order.payment_method_id = payment_method_id
        order.log(
            "payment_method_attached",
            customer_id=customer.id,
            payment_method_id=payment_method_id,
        )
        persist_order(order)
        return order

    def create_and_confirm_payment_intent(
        self,
        order_id: str,
        return_url: str,
    ) -> dict[str, Any]:
        order = get_order(order_id)

        require(order.customer_id is not None, "customer_id missing")
        require(order.payment_method_id is not None, "payment_method_id missing")
        require(order.payment_intent_id is None, "payment intent already exists")

        # Idempotency key tied to order creation step.
        idempotency_key = f"pi_create_confirm:{order.order_id}"

        # Using manual capture so successful authorization yields requires_capture.
        # Stripe supports separate confirmation and capture for this flow.
        pi = stripe.PaymentIntent.create(
            amount=order.amount,
            currency=order.currency,
            customer=order.customer_id,
            payment_method=order.payment_method_id,
            confirmation_method="manual",
            confirm=True,
            capture_method="manual",
            return_url=return_url,
            metadata={
                "order_id": order.order_id,
                "requires_review": str(order.requires_review).lower(),
            },
            idempotency_key=idempotency_key,
        )

        order.payment_intent_id = pi.id
        order.status = OrderStatus.PAYMENT_INTENT_CREATED
        order.log(
            "payment_intent_created",
            payment_intent_id=pi.id,
            status=pi.status,
        )

        self._sync_from_payment_intent(order, pi)
        persist_order(order)

        return {
            "order_id": order.order_id,
            "payment_intent_id": pi.id,
            "payment_intent_status": pi.status,
            "client_secret": pi.client_secret,
            "next_action": getattr(pi, "next_action", None),
            "order_status": order.status.value,
        }

    def confirm_after_customer_action(
        self,
        order_id: str,
    ) -> dict[str, Any]:
        """
        Server-side re-confirm step for manual confirmation flows after the client
        has handled next_action if needed.
        """
        order = get_order(order_id)
        require(order.payment_intent_id is not None, "missing payment_intent_id")

        pi = stripe.PaymentIntent.confirm(
            order.payment_intent_id,
            idempotency_key=f"pi_reconfirm:{order.order_id}",
        )

        order.log("payment_intent_reconfirmed", status=pi.status)
        self._sync_from_payment_intent(order, pi)
        persist_order(order)

        return {
            "order_id": order.order_id,
            "payment_intent_id": pi.id,
            "payment_intent_status": pi.status,
            "client_secret": pi.client_secret,
            "next_action": getattr(pi, "next_action", None),
            "order_status": order.status.value,
        }

    def approve_for_capture(
        self,
        order_id: str,
    ) -> Order:
        order = get_order(order_id)

        require(order.status == OrderStatus.AUTHORIZED, "order must be authorized first")
        if order.requires_review:
            order.approved_for_capture = True
            order.status = OrderStatus.APPROVED_FOR_CAPTURE
            order.log("capture_approved")
        else:
            # Even if review isn't required, we make approval explicit so this
            # becomes useful for formal modeling later.
            order.approved_for_capture = True
            order.status = OrderStatus.APPROVED_FOR_CAPTURE
            order.log("capture_approved_no_review_required")

        persist_order(order)
        return order

    def capture_payment(
        self,
        order_id: str,
        amount_to_capture: Optional[int] = None,
    ) -> dict[str, Any]:
        order = get_order(order_id)

        require(order.payment_intent_id is not None, "missing payment_intent_id")
        require(order.approved_for_capture, "capture not approved")
        require(order.status in {OrderStatus.AUTHORIZED, OrderStatus.APPROVED_FOR_CAPTURE},
                "order not capturable")

        capture_args: dict[str, Any] = {}
        if amount_to_capture is not None:
            require(amount_to_capture > 0, "amount_to_capture must be positive")
            require(amount_to_capture <= order.amount, "capture exceeds order amount")
            capture_args["amount_to_capture"] = amount_to_capture

        pi = stripe.PaymentIntent.capture(
            order.payment_intent_id,
            idempotency_key=f"pi_capture:{order.order_id}:{amount_to_capture or 'full'}",
            **capture_args,
        )

        order.log(
            "payment_captured",
            payment_intent_id=pi.id,
            amount_to_capture=amount_to_capture if amount_to_capture is not None else order.amount,
            status=pi.status,
        )
        self._sync_from_payment_intent(order, pi)
        persist_order(order)

        return {
            "order_id": order.order_id,
            "payment_intent_id": pi.id,
            "payment_intent_status": pi.status,
            "order_status": order.status.value,
            "amount_captured": order.amount_captured,
            "latest_charge_id": order.latest_charge_id,
        }

    def refund_payment(
        self,
        order_id: str,
        amount: Optional[int] = None,
        reason: str = "requested_by_customer",
    ) -> dict[str, Any]:
        order = get_order(order_id)

        require(order.latest_charge_id is not None, "missing latest_charge_id")
        require(order.amount_captured > 0, "nothing captured to refund")

        refundable = order.amount_captured - order.amount_refunded
        require(refundable > 0, "nothing left to refund")

        refund_amount = refundable if amount is None else amount
        require(refund_amount > 0, "refund amount must be positive")
        require(refund_amount <= refundable, "refund exceeds refundable amount")

        refund = stripe.Refund.create(
            charge=order.latest_charge_id,
            amount=refund_amount,
            reason=reason,
            idempotency_key=f"refund:{order.order_id}:{refund_amount}:{reason}",
        )

        order.amount_refunded += refund.amount
        if order.amount_refunded == order.amount_captured:
            order.status = OrderStatus.REFUNDED
        else:
            order.status = OrderStatus.PARTIALLY_REFUNDED

        order.log(
            "refund_created",
            refund_id=refund.id,
            amount=refund.amount,
            refund_status=refund.status,
            reason=reason,
        )
        persist_order(order)

        return {
            "order_id": order.order_id,
            "refund_id": refund.id,
            "refund_status": refund.status,
            "amount_refunded_total": order.amount_refunded,
            "order_status": order.status.value,
        }

    def cancel_payment_intent(
        self,
        order_id: str,
        reason: str = "requested_by_customer",
    ) -> dict[str, Any]:
        order = get_order(order_id)

        require(order.payment_intent_id is not None, "missing payment_intent_id")
        require(order.status not in {
            OrderStatus.CAPTURED,
            OrderStatus.PARTIALLY_REFUNDED,
            OrderStatus.REFUNDED,
        }, "cannot cancel after capture/refund")

        pi = stripe.PaymentIntent.cancel(order.payment_intent_id, cancellation_reason=reason)

        order.status = OrderStatus.CANCELED
        order.log(
            "payment_intent_canceled",
            payment_intent_id=pi.id,
            status=pi.status,
            cancellation_reason=reason,
        )
        persist_order(order)

        return {
            "order_id": order.order_id,
            "payment_intent_id": pi.id,
            "payment_intent_status": pi.status,
            "order_status": order.status.value,
        }

    def _sync_from_payment_intent(self, order: Order, pi: stripe.PaymentIntent) -> None:
        """
        Synchronize local state from Stripe state.
        """
        order.payment_intent_id = pi.id

        latest_charge = getattr(pi, "latest_charge", None)
        if isinstance(latest_charge, str):
            order.latest_charge_id = latest_charge
        elif latest_charge and getattr(latest_charge, "id", None):
            order.latest_charge_id = latest_charge.id

        status = pi.status

        if status == "requires_action":
            order.status = OrderStatus.REQUIRES_ACTION

        elif status == "requires_capture":
            # Authorized but not yet captured.
            order.amount_captured = 0
            order.status = OrderStatus.AUTHORIZED

        elif status == "succeeded":
            # Typically after capture in a manual-capture flow.
            amount_received = getattr(pi, "amount_received", 0) or 0
            order.amount_captured = amount_received
            order.status = OrderStatus.CAPTURED

        elif status == "canceled":
            order.status = OrderStatus.CANCELED

        elif status in {"requires_payment_method"}:
            order.status = OrderStatus.FAILED

        elif status in {"processing"}:
            # You may choose to expose a dedicated PROCESSING local state instead.
            order.status = OrderStatus.PAYMENT_INTENT_CREATED

        else:
            # Keep local state conservative.
            order.log("unhandled_payment_intent_status", stripe_status=status)

    def process_webhook_event(self, payload: bytes, sig_header: str) -> dict[str, Any]:
        """
        Verify and process Stripe webhook.
        Stripe recommends verifying webhook signatures using official libraries.
        """
        if not STRIPE_WEBHOOK_SECRET:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET not configured")

        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=STRIPE_WEBHOOK_SECRET,
        )

        event_id = event["id"]
        if event_id in PROCESSED_WEBHOOK_EVENTS:
            return {"ok": True, "duplicate": True, "event_id": event_id}

        PROCESSED_WEBHOOK_EVENTS.add(event_id)

        event_type = event["type"]
        obj = event["data"]["object"]

        if event_type.startswith("payment_intent."):
            self._handle_payment_intent_event(event_type, obj)
        elif event_type.startswith("charge."):
            self._handle_charge_event(event_type, obj)
        elif event_type.startswith("refund."):
            self._handle_refund_event(event_type, obj)
        elif event_type.startswith("charge.dispute."):
            self._handle_dispute_event(event_type, obj)

        return {"ok": True, "event_id": event_id, "event_type": event_type}

    def _handle_payment_intent_event(self, event_type: str, obj: dict[str, Any]) -> None:
        metadata = obj.get("metadata", {})
        order_id = metadata.get("order_id")
        if not order_id or order_id not in ORDERS:
            return

        order = ORDERS[order_id]
        order.payment_intent_id = obj["id"]
        if obj.get("latest_charge"):
            order.latest_charge_id = obj["latest_charge"]

        status = obj.get("status")

        if event_type == "payment_intent.requires_action":
            order.status = OrderStatus.REQUIRES_ACTION
            order.log("webhook_requires_action", event_type=event_type)

        elif event_type == "payment_intent.amount_capturable_updated":
            order.status = OrderStatus.AUTHORIZED
            order.log("webhook_amount_capturable_updated", event_type=event_type)

        elif event_type == "payment_intent.succeeded":
            order.amount_captured = obj.get("amount_received", order.amount_captured)
            order.status = OrderStatus.CAPTURED
            order.log("webhook_payment_intent_succeeded", event_type=event_type)

        elif event_type == "payment_intent.canceled":
            order.status = OrderStatus.CANCELED
            order.log("webhook_payment_intent_canceled", event_type=event_type)

        else:
            order.log("webhook_payment_intent_other", event_type=event_type, stripe_status=status)

    def _handle_charge_event(self, event_type: str, obj: dict[str, Any]) -> None:
        pi_id = obj.get("payment_intent")
        if not pi_id:
            return

        order = next((o for o in ORDERS.values() if o.payment_intent_id == pi_id), None)
        if not order:
            return

        order.latest_charge_id = obj["id"]

        if event_type == "charge.succeeded":
            order.log("webhook_charge_succeeded", charge_id=obj["id"])

        elif event_type == "charge.refunded":
            amount_refunded = obj.get("amount_refunded", 0)
            order.amount_refunded = amount_refunded
            if order.amount_refunded >= order.amount_captured:
                order.status = OrderStatus.REFUNDED
            else:
                order.status = OrderStatus.PARTIALLY_REFUNDED
            order.log(
                "webhook_charge_refunded",
                charge_id=obj["id"],
                amount_refunded=amount_refunded,
            )

        elif event_type == "charge.failed":
            order.status = OrderStatus.FAILED
            order.log("webhook_charge_failed", charge_id=obj["id"])

    def _handle_refund_event(self, event_type: str, obj: dict[str, Any]) -> None:
        charge_id = obj.get("charge")
        if not charge_id:
            return

        order = next((o for o in ORDERS.values() if o.latest_charge_id == charge_id), None)
        if not order:
            return

        order.log(
            "webhook_refund_event",
            event_type=event_type,
            refund_id=obj.get("id"),
            refund_status=obj.get("status"),
            amount=obj.get("amount"),
        )

    def _handle_dispute_event(self, event_type: str, obj: dict[str, Any]) -> None:
        charge_id = obj.get("charge")
        if not charge_id:
            return

        order = next((o for o in ORDERS.values() if o.latest_charge_id == charge_id), None)
        if not order:
            return

        if event_type in {"charge.dispute.created", "charge.dispute.updated"}:
            order.status = OrderStatus.DISPUTED
            order.log(
                "webhook_dispute_open_or_updated",
                dispute_id=obj.get("id"),
                dispute_status=obj.get("status"),
                amount=obj.get("amount"),
                reason=obj.get("reason"),
            )

        elif event_type == "charge.dispute.closed":
            # Keep status conservative; real business logic may branch on won/lost.
            order.log(
                "webhook_dispute_closed",
                dispute_id=obj.get("id"),
                dispute_status=obj.get("status"),
            )


# =============================================================================
# Simple HTTP layer
# =============================================================================

flow = StripePaymentFlow()


@app.post("/orders")
def create_order_route():
    body = request.get_json(force=True)
    order = flow.create_order(
        order_id=body["order_id"],
        amount=body["amount"],
        currency=body["currency"],
        customer_email=body["customer_email"],
        requires_review=body.get("requires_review", False),
    )
    return jsonify(asdict(order))


@app.post("/orders/<order_id>/attach-payment-method")
def attach_payment_method_route(order_id: str):
    body = request.get_json(force=True)
    order = flow.attach_payment_method_to_customer(
        order_id=order_id,
        payment_method_id=body["payment_method_id"],
    )
    return jsonify(asdict(order))


@app.post("/orders/<order_id>/create-and-confirm")
def create_and_confirm_route(order_id: str):
    body = request.get_json(force=True)
    result = flow.create_and_confirm_payment_intent(
        order_id=order_id,
        return_url=body["return_url"],
    )
    return jsonify(result)


@app.post("/orders/<order_id>/reconfirm")
def reconfirm_route(order_id: str):
    result = flow.confirm_after_customer_action(order_id=order_id)
    return jsonify(result)


@app.post("/orders/<order_id>/approve")
def approve_route(order_id: str):
    order = flow.approve_for_capture(order_id=order_id)
    return jsonify(asdict(order))


@app.post("/orders/<order_id>/capture")
def capture_route(order_id: str):
    body = request.get_json(force=True, silent=True) or {}
    result = flow.capture_payment(
        order_id=order_id,
        amount_to_capture=body.get("amount_to_capture"),
    )
    return jsonify(result)


@app.post("/orders/<order_id>/refund")
def refund_route(order_id: str):
    body = request.get_json(force=True, silent=True) or {}
    result = flow.refund_payment(
        order_id=order_id,
        amount=body.get("amount"),
        reason=body.get("reason", "requested_by_customer"),
    )
    return jsonify(result)


@app.post("/orders/<order_id>/cancel")
def cancel_route(order_id: str):
    body = request.get_json(force=True, silent=True) or {}
    result = flow.cancel_payment_intent(
        order_id=order_id,
        reason=body.get("reason", "requested_by_customer"),
    )
    return jsonify(result)


@app.get("/orders/<order_id>")
def get_order_route(order_id: str):
    order = get_order(order_id)
    return jsonify(asdict(order))


@app.post("/webhooks/stripe")
def stripe_webhook_route():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        result = flow.process_webhook_event(payload=payload, sig_header=sig_header)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


# =============================================================================
# Example manual runner
# =============================================================================

def demo_sequence() -> None:
    """
    Illustrative sequence; the actual 3DS step requires client-side handling.

    Example test payment method IDs are created or supplied by your frontend.
    In a real integration, your frontend collects card details via Stripe.js /
    Payment Element and gives you a PaymentMethod ID or confirms client-side.
    """
    order = flow.create_order(
        order_id="order_1001",
        amount=15000,  # $150.00
        currency="usd",
        customer_email="alice@example.com",
        requires_review=True,
    )

    print("ORDER CREATED")
    print(json.dumps(asdict(order), indent=2))

    # Example only: replace with a real PM from test frontend collection.
    payment_method_id = "pm_card_threeDSecure2Required"

    flow.attach_payment_method_to_customer(order.order_id, payment_method_id)

    result = flow.create_and_confirm_payment_intent(
        order_id=order.order_id,
        return_url="https://example.com/return",
    )
    print("\nCREATE+CONFIRM RESULT")
    print(json.dumps(result, indent=2, default=str))

    # If result["payment_intent_status"] == "requires_action",
    # the frontend must handle next_action using Stripe.js and then call
    # /orders/<order_id>/reconfirm or just wait for webhooks depending on flow.

    # Suppose the intent eventually becomes authorized:
    # flow.approve_for_capture(order.order_id)
    # flow.capture_payment(order.order_id, amount_to_capture=12000)
    # flow.refund_payment(order.order_id, amount=2000)


if __name__ == "__main__":
    # For local API testing:
    #   FLASK_APP=stripe_payment_flow.py flask run --port 8000
    #
    # Or run the demo directly:
    #   python stripe_payment_flow.py
    #
    # Uncomment one of the following as desired.

    # demo_sequence()
    app.run(host="0.0.0.0", port=8000, debug=True)
