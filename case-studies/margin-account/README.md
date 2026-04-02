# Margin Account Engine Verification

## Overview

Regulatory margin enforcement in leveraged trading accounts. This case study models the state machine that brokers use to monitor client equity and trigger forced liquidation when margin thresholds are breached. It references the 2021 Archegos Capital collapse, which resulted in $10+ billion in losses across multiple prime brokers due to inadequate margin enforcement.

## The Problem

When clients borrow money for margin trading, brokers must continuously monitor equity positions. Failure to enforce liquidation triggers exposes institutions to unlimited losses if clients become insolvent.

**Regulatory Requirements:**

- **Regulation T (Federal Reserve): Initial Margin 50%** -- the minimum equity required when opening new positions.
- **FINRA Rule 4210: Maintenance Margin 25%** -- the minimum equity to avoid liquidation. A breach of this threshold triggers forced asset liquidation.

## State Machine Model

Three account health states govern what actions are permitted:

| State | Condition | Allowed Actions |
|-------|-----------|-----------------|
| HEALTHY | Equity Ratio >= 50% | Open positions, withdraw funds |
| RESTRICTED | 25% <= Equity Ratio < 50% | Hold positions only |
| LIQUIDATION_CALL | Equity Ratio < 25% | Must liquidate assets |

## Original Python Implementation

The core status check determines which state the account is in based on the current equity ratio:

```python
def check_status(self) -> AccountStatus:
    equity_ratio = self.calculate_equity_ratio()
    if equity_ratio is None:
        return AccountStatus.HEALTHY
    if equity_ratio < self.margin_requirements.maintenance_margin_pct / Decimal("100"):
        return AccountStatus.LIQUIDATION_CALL
    if equity_ratio < self.margin_requirements.initial_margin_pct / Decimal("100"):
        return AccountStatus.RESTRICTED
    return AccountStatus.HEALTHY
```

**Key Calculations:**

- Equity = Cash + MarketValue - Loan
- EquityRatio = Equity / MarketValue

## Real-World Scenario

**Initial Position:**

| Field | Value |
|-------|-------|
| Cash | $10,000 |
| Shares | 100 @ $400 |
| Market Value | $40,000 |
| Loan | $30,000 |
| Equity | $20,000 |
| Equity Ratio | 50% |
| Status | HEALTHY |

**After 40% Market Decline:**

| Field | Value |
|-------|-------|
| Market Value | $24,000 |
| Equity | $4,000 |
| Equity Ratio | 16.7% |
| Status | LIQUIDATION_CALL |

## IML Formal Model

The formal model is defined in `margin_account_engine.iml`. It encodes the state machine, margin calculations, and transition logic so that properties can be verified automatically.

## Verification Results

| Property | What Was Proved | Status |
|----------|-----------------|--------|
| Solvency Safety | Low equity MUST trigger liquidation | PROVED |
| No Gap Risk | No withdrawal immediately causes margin call | PROVED |
| Withdrawal Protection | Withdrawals maintain initial margin | PROVED |

## Running the Demo

```bash
# Type-check the model
codelogician-lite check margin_account_engine.iml

# Run verification goals
codelogician-lite check-vg margin_account_engine.iml
```

## Source

Original case study: [codelogician.dev/docs/industry-case-studies/margin-account-engine-verification](https://codelogician.dev/docs/industry-case-studies/margin-account-engine-verification/)
