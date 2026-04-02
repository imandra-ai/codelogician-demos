# LSE Stop Orders Verification

## Overview

Extended functionality bypassing MIT201 specification rules. Formal verification validates core implementation and finds bug.

## The Problem

Stop and Stop Limit orders on the London Stock Exchange must follow MIT201 Section 5.2 specifications. A fundamental safety invariant: buy and sell stop orders should never elect simultaneously.

**Election Rules:**
- **Buy Stop Orders:** Elect when Last Automated Trade Price (LATP) rises to or above the stop price
- **Sell Stop Orders:** Elect when LATP falls to or below the stop price

**MIT201 Core Rules:**
- **Rule 1:** Elect on entry if stop price already reached
- **Rule 2:** Park if no LATP (no trading yet)
- **Rule 3:** Buy elects when LATP >= stop price
- **Rule 4:** Sell elects when LATP <= stop price

## Original Python Implementation (Buggy)

The original system added extended functionality for large orders that bypassed all MIT201 rules:

```python
def maybe_elect_stop_order(latp: Optional[Price], stop_order: StopOrder) -> OrderSlot:
    # Extended functionality (NOT part of MIT201)
    if stop_order.qty > 1000:
        return elect_stop_order(stop_order)  # BYPASSES ALL MIT201 RULES

    # MIT201 compliant logic below...
    if stop_price_is_reached(latp, stop_order):
        return elect_stop_order(stop_order)
    else:
        return park_stop_order(stop_order)
```

## The Bug - Counterexample

CodeLogician discovered:

**Initial State:**
- LATP: 4064
- Buy Stop Order: qty = 1, stop_price = 2276
- Sell Stop Order: qty = 1143, stop_price = 4064

**Event:** Trade executes at price 2276

**Result:** Both orders elected simultaneously -- violating the safety property. The sell order with qty > 1000 bypasses MIT201 rules entirely.

## The Fix

```python
def maybe_elect_stop_order(latp: Optional[Price], stop_order: StopOrder) -> OrderSlot:
    # REMOVE the hack completely
    # Keep only MIT201-compliant logic:
    if stop_price_is_reached(latp, stop_order):
        return elect_stop_order(stop_order)
    else:
        return park_stop_order(stop_order)
```

## IML Formal Model

The `lse_stop_orders.iml` file contains the formal model of the stop order system using the fixed version (no large-order bypass). The verification goal checks whether both buy and sell stop orders can elect simultaneously under valid market conditions.

## Verification Results

| Goal | Result | What it shows |
|------|--------|---------------|
| No simultaneous election under valid state | **REFUTED** | Counterexample: LATP between buy_stop and sell_stop triggers both |

Verification time: < 1 minute.

## Running the Demo

```bash
# Type-check the model
codelogician-lite check lse_stop_orders.iml

# Run the verification goal (will produce a counterexample)
codelogician-lite check-vg lse_stop_orders.iml
```

## Source

Original case study: [codelogician.dev/docs/industry-case-studies/lse-stop-orders-verification](https://codelogician.dev/docs/industry-case-studies/lse-stop-orders-verification/)
