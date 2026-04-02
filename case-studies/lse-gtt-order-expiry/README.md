# LSE GTT Order Expiry Verification

## Overview

Critical regulatory compliance bug in auction order expiry logic. Formal verification discovers a race condition between GTT order expiry and auction uncross events in the London Stock Exchange trading system specification.

## The Problem

The London Stock Exchange (LSE) Guide to Trading System (MIT201) specifies:

> "Any GTT orders with an expiry time during any auction call phase will not be expired until after uncrossing has completed and are therefore eligible to participate in that uncrossing."

A critical bug was discovered where GTT orders can expire simultaneously with auction uncross events, violating this requirement and potentially excluding orders from auctions they should participate in.

## System Components

- **Trading Modes:** Continuous (normal trading) and Auction Call (pre-auction phase with a scheduled uncross time).
- **GTT Orders:** Good Till Time orders with expiry timestamps. Auction protection is supposed to delay expiry during auctions so these orders can participate in the uncross.
- **Market Order Extension:** An extension period triggered when market orders remain after uncross. The effective uncross time becomes the original uncross time plus the extension period.

## The Bug - Counterexample

CodeLogician discovered a concrete counterexample demonstrating the violation:

**Initial State (t=2699):**

| Field | Value |
|---|---|
| time | 2699 |
| mode | AuctionCallMode { uncross_at: 2700 } |
| gtt_order | Some { expires_at: 2700 } |
| market_order_present_after_uncross | true |
| market_order_extension_period | 1 |

**Messages:** `[Tick, Tick]`

**Conflict at t=2701:**

- Auction uncrosses at t=2701 because `2701 >= 2700 + extension(1)`.
- GTT order expires at t=2701 because `2701 >= extended_expiry(2701)`.
- Result: Both events fire simultaneously -- this is a MIT201 violation. The order should have participated in the uncross but was expired at the same instant.

## Why Traditional Testing Missed This

- Requires exact timing alignment of order expiry, auction uncross, and market order extension.
- The bug only manifests when `extension_period = 1` (would need exhaustive testing of all extension values).
- Individual features work correctly in isolation -- the bug emerges from the interaction of three features at a precise boundary condition.

## IML Formal Model

The file `lse_gtt_expiry.iml` models the core trading system behavior:

- **State:** Tracks the current time, trading mode (Continuous or Auction Call), an optional GTT order, auction/order events, and market order extension parameters.
- **Messages:** `Tick` advances time by one unit; `CreateGTTOrder` places a new order with a given expiry.
- **Mode transitions:** In Continuous mode, an auction call starts when the scheduled time arrives. In Auction Call mode, uncrossing occurs when time reaches `uncross_at` (plus any market order extension).
- **GTT expiry (original, buggy):** The order expires when `time >= expires_at`, with no awareness of whether an auction uncross is happening at the same instant.
- **GTT expiry (V2, fixed):** During an Auction Call, if the order's expiry falls at or before the scheduled uncross time, the effective expiry is pushed to `uncross_at + 1`. This guarantees the order survives through the uncross and participates in it.
- **Conflict detection:** The property `conflict_detected` checks whether an uncross and an order expiry occur in the same step -- a direct violation of MIT201.

## Verification Results

CodeLogician formally verifies:

- **Buggy version:** A counterexample is found in 2 steps (the Tick, Tick sequence above), proving the race condition exists.
- **Fixed V2 version:** No counterexample exists. The conflict property is unreachable, providing a mathematical proof that the fix eliminates the race condition for all possible inputs and timing combinations.

## Business Impact

**Without Formal Verification:**
- Manual test design takes days and edge cases are likely missed.
- Bug discovery takes weeks or months, often only after it surfaces in production.
- Regulatory penalties and customer compensation follow.

**With CodeLogician:**
- Formalization in minutes.
- Bug discovery is immediate.
- Zero production incidents.
- Mathematical proof of correctness for the fix.

## Running the Demo

```bash
# Type-check the model
codelogician-lite check lse_gtt_expiry.iml
```

## Source

Original case study: [codelogician.dev/docs/industry-case-studies/lse-gtt-order-expiry-verification](https://codelogician.dev/docs/industry-case-studies/lse-gtt-order-expiry-verification/)
