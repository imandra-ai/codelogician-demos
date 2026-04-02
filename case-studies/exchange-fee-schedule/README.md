# Exchange Fee Schedule Verification

## Overview

Complex fee schedule with tiered pricing, rebates, and minimum floors. Formal verification of the London Stock Exchange Trading Services Price List (January 2025).

## The Problem

Financial firms must accurately predict trading fees before sending orders. A single basis point error across millions of daily trades can cause revenue leakage, unexpected costs, or regulatory violations.

Fee schedules are notoriously difficult to model due to:

- Opaque PDF specifications with tables and footnotes
- Complex interactions between tiered pricing, minimums, rebates, and surcharges
- Frequent schedule updates
- Need for regulatory audit trails

## Original Python Implementation

The tiered rate function from the production Python codebase illustrates how cumulative monthly trading volume determines the applicable rate:

```python
def get_tiered_rate(cumulative_value_gbp: Decimal) -> Decimal:
    """
    Get the standard scheme rate based on cumulative MTD value.

    [PDF:P4:STANDARD_TIERS]
    - First £3.5bn: 0.45bp
    - Next £5bn (to £8.5bn): 0.35bp
    - All subsequent: 0.25bp
    """
    if cumulative_value_gbp < TIER_1_THRESHOLD_GBP:
        return TIER_1_RATE_BP
    elif cumulative_value_gbp < TIER_2_THRESHOLD_GBP:
        return TIER_2_RATE_BP
    else:
        return TIER_3_RATE_BP
```

## Key Findings

### Tiered Rate Regions

| Region | Constraint | Rate |
|--------|-----------|------|
| 1 | cumulative < £3.5bn | 0.45bp |
| 2 | £3.5bn ≤ cumulative < £8.5bn | 0.35bp |
| 3 | cumulative ≥ £8.5bn | 0.25bp |

### Small Trade Penalty

Minimum charge floors create effective rates dramatically higher than stated rates for small trades.

Example: £1,000 trade at 0.45bp rate:

- **Calculated fee**: £1,000 x 0.45bp x 0.0001 = **£0.045**
- **Minimum floor**: **£0.11**
- **Effective rate**: **11bp** (24x the stated rate)

### Crossover Notional by Scheme

The crossover notional is where the proportional fee equals the minimum floor -- trades below this size pay the minimum instead.

| Scheme | Rate (bp) | Min (p) | Crossover Notional |
|--------|-----------|---------|-------------------|
| Standard (Tier 1) | 0.45 | 11 | £2,444 |
| Standard (Tier 2) | 0.35 | 11 | £3,143 |
| Standard (Tier 3) | 0.25 | 11 | £4,400 |
| Package 1 | 0.15 | 5 | £3,333 |
| Package 1 Prop | 0.15 | 10 | £6,667 |
| Package 2 | 0.28 | 10 | £3,571 |

## IML Formal Model

The formal model is defined in [`lse_equity_fees.iml`](lse_equity_fees.iml). It encodes:

- **Type definitions** for packages (Standard, Pkg1, Pkg1_prop, Pkg2), LPS tiers, security types, and time-in-force
- **Order entry charges** per package and time-in-force (DAY orders are free; IOC/FOK cost £0.01)
- **Execution rate and minimum charge** lookup across all 20 package/LPS/security combinations
- **Fee calculation** with minimum floor logic: if the raw fee (consideration x rate / 10000) is below the minimum charge, the minimum applies
- **Two verification goals** (VG1: Penny Jump, VG2: LPS Zero-Fee)
- **Region decomposition** of `calculate_execution_fee`

## Verification Results

| Goal | Result | What it proves |
|------|--------|----------------|
| VG1: Penny Jump -- IOC/FOK costs exactly £0.01 more than DAY | **PROVED** | Entry charge difference is exactly 1 penny for any trade |
| VG2: LPS Zero-Fee -- execution fee = 0 at LPS Tier 3 | **PROVED** | Top-tier liquidity providers pay no execution fee |

### Region Decomposition

Decomposition of `calculate_execution_fee` discovered **6 behavioral regions** (expected 2-3):

| # | Rate | Min Dominates | Formula |
|---|------|---------------|---------|
| 1 | >= 0 | Yes | `min_charge` |
| 2 | >= 0 | No | `notional x rate x 0.0001` |
| 3 | >= 0 | Yes | `min_charge` (hidden region) |
| 4 | >= 0 | No | `notional x (rate + 0.25) x 0.0001` (hidden region) |
| 5 | < 0 | N/A | `notional x rate x 0.0001` |
| 6 | < 0 | N/A | `notional x (rate + 0.25) x 0.0001` (hidden region) |

The hidden regions represent edge cases not apparent from reading the code but discovered through formal analysis.

## Running the Demo

```bash
# Type-check the model
codelogician-lite check lse_equity_fees.iml

# Run verification goals
codelogician-lite check-vg lse_equity_fees.iml

# Run region decomposition
codelogician-lite check-decomp lse_equity_fees.iml
```

## Source

Original case study: [codelogician.dev/docs/industry-case-studies/exchange-fee-schedule-verification](https://codelogician.dev/docs/industry-case-studies/exchange-fee-schedule-verification/)
