from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OrderStatus(str, Enum):
    CREATED = "Created"
    PAYMENT_INTENT_CREATED = "PaymentIntentCreated"
    REQUIRES_ACTION = "RequiresAction"
    AUTHORIZED = "Authorized"
    APPROVED_FOR_CAPTURE = "ApprovedForCapture"
    CAPTURED = "Captured"
    PARTIALLY_REFUNDED = "PartiallyRefunded"
    REFUNDED = "Refunded"
    DISPUTED = "Disputed"
    CANCELED = "Canceled"
    FAILED = "Failed"


class ActionKind(str, Enum):
    CREATE_PAYMENT_INTENT = "ActCreatePaymentIntent"
    CONFIRM_PAYMENT_INTENT = "ActConfirmPaymentIntent"
    COMPLETE_THREE_DS = "ActCompleteThreeDS"
    APPROVE_FOR_CAPTURE = "ActApproveForCapture"
    CAPTURE = "ActCapture"
    REFUND = "ActRefund"
    CANCEL_PAYMENT_INTENT = "ActCancelPaymentIntent"
    OPEN_DISPUTE = "ActOpenDispute"


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    amount: Optional[int] = None


@dataclass(frozen=True)
class Order:
    amount: int
    amount_captured: int
    amount_refunded: int
    status: OrderStatus
    requires_review: bool
    high_risk: bool
    three_ds_required: bool
    three_ds_completed: bool
    approval_count: int
    payment_intent_exists: bool
    latest_charge_exists: bool


# -----------------------------------------------------------------------------
# Constructors / helpers
# -----------------------------------------------------------------------------


def init_order(
    amount: int,
    requires_review: bool,
    high_risk: bool,
    three_ds_required: bool,
) -> Order:
    return Order(
        amount=amount,
        amount_captured=0,
        amount_refunded=0,
        status=OrderStatus.CREATED,
        requires_review=requires_review,
        high_risk=high_risk,
        three_ds_required=three_ds_required,
        three_ds_completed=False,
        approval_count=0,
        payment_intent_exists=False,
        latest_charge_exists=False,
    )



def replace(order: Order, **changes) -> Order:
    data = {
        "amount": order.amount,
        "amount_captured": order.amount_captured,
        "amount_refunded": order.amount_refunded,
        "status": order.status,
        "requires_review": order.requires_review,
        "high_risk": order.high_risk,
        "three_ds_required": order.three_ds_required,
        "three_ds_completed": order.three_ds_completed,
        "approval_count": order.approval_count,
        "payment_intent_exists": order.payment_intent_exists,
        "latest_charge_exists": order.latest_charge_exists,
    }
    data.update(changes)
    return Order(**data)


# -----------------------------------------------------------------------------
# Core predicates
# -----------------------------------------------------------------------------


def valid_amounts(o: Order) -> bool:
    return (
        0 <= o.amount
        and 0 <= o.amount_captured
        and 0 <= o.amount_refunded
        and o.amount_refunded <= o.amount_captured
        and o.amount_captured <= o.amount
    )



def required_approvals(o: Order) -> int:
    if o.high_risk:
        return 2
    if o.requires_review:
        return 1
    return 0



def may_capture(o: Order) -> bool:
    return (
        o.status in {OrderStatus.AUTHORIZED, OrderStatus.APPROVED_FOR_CAPTURE}
        and o.latest_charge_exists
        and ((not o.three_ds_required) or o.three_ds_completed)
        and o.approval_count >= required_approvals(o)
    )


# -----------------------------------------------------------------------------
# Transition functions
# -----------------------------------------------------------------------------


def create_payment_intent(o: Order) -> Order:
    if o.status == OrderStatus.CREATED and o.amount > 0:
        return replace(
            o,
            status=OrderStatus.PAYMENT_INTENT_CREATED,
            payment_intent_exists=True,
        )
    return o



def confirm_payment_intent(o: Order) -> Order:
    if o.status == OrderStatus.PAYMENT_INTENT_CREATED and o.payment_intent_exists:
        if o.three_ds_required and not o.three_ds_completed:
            return replace(o, status=OrderStatus.REQUIRES_ACTION)
        return replace(
            o,
            status=OrderStatus.AUTHORIZED,
            latest_charge_exists=True,
        )
    return o



def complete_three_ds(o: Order) -> Order:
    if o.status == OrderStatus.REQUIRES_ACTION and o.three_ds_required:
        return replace(
            o,
            three_ds_completed=True,
            status=OrderStatus.AUTHORIZED,
            latest_charge_exists=True,
        )
    return o



def approve_for_capture(o: Order) -> Order:
    if o.status in {OrderStatus.AUTHORIZED, OrderStatus.APPROVED_FOR_CAPTURE}:
        return replace(
            o,
            approval_count=o.approval_count + 1,
            status=OrderStatus.APPROVED_FOR_CAPTURE,
        )
    return o



def capture_payment(amount: int, o: Order) -> Order:
    if may_capture(o) and amount > 0 and amount <= o.amount:
        return replace(
            o,
            amount_captured=amount,
            amount_refunded=0,
            status=OrderStatus.CAPTURED,
        )
    return o



def refund_payment(amount: int, o: Order) -> Order:
    remaining = o.amount_captured - o.amount_refunded
    if (
        o.status in {OrderStatus.CAPTURED, OrderStatus.PARTIALLY_REFUNDED}
        and amount > 0
        and amount <= remaining
    ):
        new_refunded = o.amount_refunded + amount
        new_status = (
            OrderStatus.REFUNDED
            if new_refunded == o.amount_captured
            else OrderStatus.PARTIALLY_REFUNDED
        )
        return replace(
            o,
            amount_refunded=new_refunded,
            status=new_status,
        )
    return o



def cancel_payment_intent(o: Order) -> Order:
    if (
        o.payment_intent_exists
        and o.status != OrderStatus.CAPTURED
        and o.status != OrderStatus.PARTIALLY_REFUNDED
        and o.status != OrderStatus.REFUNDED
    ):
        return replace(o, status=OrderStatus.CANCELED)
    return o



def open_dispute(o: Order) -> Order:
    if o.status in {OrderStatus.CAPTURED, OrderStatus.PARTIALLY_REFUNDED}:
        return replace(o, status=OrderStatus.DISPUTED)
    return o



def step(action: Action, o: Order) -> Order:
    if action.kind == ActionKind.CREATE_PAYMENT_INTENT:
        return create_payment_intent(o)
    if action.kind == ActionKind.CONFIRM_PAYMENT_INTENT:
        return confirm_payment_intent(o)
    if action.kind == ActionKind.COMPLETE_THREE_DS:
        return complete_three_ds(o)
    if action.kind == ActionKind.APPROVE_FOR_CAPTURE:
        return approve_for_capture(o)
    if action.kind == ActionKind.CAPTURE:
        return capture_payment(action.amount or 0, o)
    if action.kind == ActionKind.REFUND:
        return refund_payment(action.amount or 0, o)
    if action.kind == ActionKind.CANCEL_PAYMENT_INTENT:
        return cancel_payment_intent(o)
    if action.kind == ActionKind.OPEN_DISPUTE:
        return open_dispute(o)
    return o


# -----------------------------------------------------------------------------
# Invariants / goals mirroring the updated IML model
# -----------------------------------------------------------------------------


def inv_amounts(o: Order) -> bool:
    return (
        0 <= o.amount
        and 0 <= o.amount_captured
        and 0 <= o.amount_refunded
        and o.amount_refunded <= o.amount_captured
        and o.amount_captured <= o.amount
    )



def inv_capture_requires_policy(o: Order) -> bool:
    return o.status != OrderStatus.CAPTURED or o.approval_count >= required_approvals(o)



def inv_high_risk_two_approvals(o: Order) -> bool:
    return (not o.high_risk) or o.status != OrderStatus.CAPTURED or o.approval_count >= 2



def inv_refund_bounded(o: Order) -> bool:
    return o.amount_refunded <= o.amount_captured



def inv_capture_bounded(o: Order) -> bool:
    return o.amount_captured <= o.amount



def inv_no_cancel_after_capture_result(o: Order) -> bool:
    return o.status not in {
        OrderStatus.CAPTURED,
        OrderStatus.PARTIALLY_REFUNDED,
        OrderStatus.REFUNDED,
    } or o.status != OrderStatus.CANCELED



def goal_no_high_risk_capture_with_one_approval(amount: int, o: Order) -> bool:
    if o.high_risk and o.approval_count < 2:
        return capture_payment(amount, o).status != OrderStatus.CAPTURED
    return True



def goal_no_cancel_after_capture_like_states(o: Order) -> bool:
    if o.status in {OrderStatus.CAPTURED, OrderStatus.PARTIALLY_REFUNDED, OrderStatus.REFUNDED}:
        return cancel_payment_intent(o).status != OrderStatus.CANCELED
    return True



def goal_no_refund_before_capture(amount: int, o: Order) -> bool:
    if o.status not in {OrderStatus.CAPTURED, OrderStatus.PARTIALLY_REFUNDED}:
        new_o = refund_payment(amount, o)
        return new_o.status not in {OrderStatus.PARTIALLY_REFUNDED, OrderStatus.REFUNDED}
    return True



def goal_3ds_required_blocks_authorization(o: Order) -> bool:
    if (
        o.status == OrderStatus.PAYMENT_INTENT_CREATED
        and o.three_ds_required
        and not o.three_ds_completed
    ):
        return confirm_payment_intent(o).status == OrderStatus.REQUIRES_ACTION
    return True



def goal_3ds_completion_enables_authorization(o: Order) -> bool:
    if o.status == OrderStatus.REQUIRES_ACTION and o.three_ds_required:
        return complete_three_ds(o).status == OrderStatus.AUTHORIZED
    return True



def goal_high_risk_3ds_capture_requires_both(amount: int, o: Order) -> bool:
    if o.high_risk and o.three_ds_required and ((not o.three_ds_completed) or o.approval_count < 2):
        return capture_payment(amount, o).status != OrderStatus.CAPTURED
    return True


# -----------------------------------------------------------------------------
# Scenario helpers
# -----------------------------------------------------------------------------


def run_actions(o: Order, actions: list[Action]) -> Order:
    cur = o
    for act in actions:
        cur = step(act, cur)
    return cur



def low_risk_happy_path() -> Order:
    o0 = init_order(10000, False, False, False)
    return run_actions(
        o0,
        [
            Action(ActionKind.CREATE_PAYMENT_INTENT),
            Action(ActionKind.CONFIRM_PAYMENT_INTENT),
            Action(ActionKind.CAPTURE, 10000),
        ],
    )



def review_path() -> Order:
    o0 = init_order(10000, True, False, False)
    return run_actions(
        o0,
        [
            Action(ActionKind.CREATE_PAYMENT_INTENT),
            Action(ActionKind.CONFIRM_PAYMENT_INTENT),
            Action(ActionKind.APPROVE_FOR_CAPTURE),
            Action(ActionKind.CAPTURE, 10000),
        ],
    )



def high_risk_one_approval_attempt() -> Order:
    o0 = init_order(10000, True, True, False)
    return run_actions(
        o0,
        [
            Action(ActionKind.CREATE_PAYMENT_INTENT),
            Action(ActionKind.CONFIRM_PAYMENT_INTENT),
            Action(ActionKind.APPROVE_FOR_CAPTURE),
            Action(ActionKind.CAPTURE, 10000),
        ],
    )



def high_risk_two_approval_path() -> Order:
    o0 = init_order(10000, True, True, False)
    return run_actions(
        o0,
        [
            Action(ActionKind.CREATE_PAYMENT_INTENT),
            Action(ActionKind.CONFIRM_PAYMENT_INTENT),
            Action(ActionKind.APPROVE_FOR_CAPTURE),
            Action(ActionKind.APPROVE_FOR_CAPTURE),
            Action(ActionKind.CAPTURE, 10000),
        ],
    )



def three_ds_path() -> Order:
    o0 = init_order(10000, False, False, True)
    return run_actions(
        o0,
        [
            Action(ActionKind.CREATE_PAYMENT_INTENT),
            Action(ActionKind.CONFIRM_PAYMENT_INTENT),
            Action(ActionKind.COMPLETE_THREE_DS),
            Action(ActionKind.CAPTURE, 10000),
        ],
    )



def high_risk_three_ds_one_approval_attempt() -> Order:
    o0 = init_order(10000, True, True, True)
    return run_actions(
        o0,
        [
            Action(ActionKind.CREATE_PAYMENT_INTENT),
            Action(ActionKind.CONFIRM_PAYMENT_INTENT),
            Action(ActionKind.COMPLETE_THREE_DS),
            Action(ActionKind.APPROVE_FOR_CAPTURE),
            Action(ActionKind.CAPTURE, 10000),
        ],
    )



def high_risk_three_ds_two_approval_path() -> Order:
    o0 = init_order(10000, True, True, True)
    return run_actions(
        o0,
        [
            Action(ActionKind.CREATE_PAYMENT_INTENT),
            Action(ActionKind.CONFIRM_PAYMENT_INTENT),
            Action(ActionKind.COMPLETE_THREE_DS),
            Action(ActionKind.APPROVE_FOR_CAPTURE),
            Action(ActionKind.APPROVE_FOR_CAPTURE),
            Action(ActionKind.CAPTURE, 10000),
        ],
    )



def partial_refund_path() -> Order:
    o0 = init_order(10000, False, False, False)
    return run_actions(
        o0,
        [
            Action(ActionKind.CREATE_PAYMENT_INTENT),
            Action(ActionKind.CONFIRM_PAYMENT_INTENT),
            Action(ActionKind.CAPTURE, 10000),
            Action(ActionKind.REFUND, 3000),
        ],
    )


if __name__ == "__main__":
    examples = {
        "low_risk_happy_path": low_risk_happy_path(),
        "review_path": review_path(),
        "high_risk_one_approval_attempt": high_risk_one_approval_attempt(),
        "high_risk_two_approval_path": high_risk_two_approval_path(),
        "three_ds_path": three_ds_path(),
        "high_risk_three_ds_one_approval_attempt": high_risk_three_ds_one_approval_attempt(),
        "high_risk_three_ds_two_approval_path": high_risk_three_ds_two_approval_path(),
        "partial_refund_path": partial_refund_path(),
    }

    for name, order in examples.items():
        print(f"{name}: {order}")
