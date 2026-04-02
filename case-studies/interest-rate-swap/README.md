# Interest Rate Swap Schedule Generator

## Overview

Business day adjustment logic in swap scheduling with subtle edge cases. Interest rate swaps represent over $400 trillion in notional outstanding globally, making them the largest segment of the derivatives market. Even small errors in payment date calculations can cascade into significant financial discrepancies across thousands of contracts.

## The Problem

Companies borrowing at floating rates face unpredictable payments. A swap allows them to exchange floating-rate payments for fixed ones, making budgeting predictable. One party pays a fixed rate; the other pays a floating rate (e.g., SOFR). Both sides need to agree on exact payment dates and amounts for the life of the contract.

The scheduler's job: generate accurate payment schedules spanning 2-10 years, including:

- All payment dates across the life of the swap
- Business day adjustments (weekend avoidance) so no payment falls on a non-business day
- Day count fractions for interest calculations
- Fixed payment amounts per period

## Original Python Implementation

The core weekend adjustment function uses the "Following" convention — if a date falls on a weekend, move it forward to the next Monday:

```python
def adjust_business_day_following(date: date) -> date:
    """
    Adjust a date to the following business day if it falls on a weekend.
    Following convention: Move forward to next business day.
    """
    weekday = date.weekday()  # 0=Monday, 6=Sunday
    if weekday == 5:  # Saturday
        return date + timedelta(days=2)  # Move to Monday
    elif weekday == 6:  # Sunday
        return date + timedelta(days=1)  # Move to Monday
    else:
        return date  # Weekday, no adjustment needed
```

This looks simple, but the interaction between date arithmetic and business day adjustment creates subtle edge cases that are difficult to catch with conventional testing.

## Real-World Example

**Swap Contract Terms:**

| Parameter | Value |
|-----------|-------|
| Start Date | January 15, 2024 |
| Maturity | January 15, 2026 |
| Term | 2 years |
| Notional | $10,000,000 |
| Fixed Rate | 4.5% |
| Frequency | Quarterly |
| Per Quarter | $10M x 4.5% / 4 = **$112,500** |

**Payment Schedule:**

| Period | Scheduled Date | Day | Adjusted Date | Day | Adjustment | Day Count Fraction | Fixed Payment |
|--------|---------------|-----|---------------|-----|------------|-------------------|---------------|
| 1 | Apr 15, 2024 | Mon | Apr 15, 2024 | Mon | None | 0.2528 | $112,500.00 |
| 2 | Jul 15, 2024 | Mon | Jul 15, 2024 | Mon | None | 0.2528 | $112,500.00 |
| 3 | Oct 15, 2024 | Tue | Oct 15, 2024 | Tue | None | 0.2556 | $112,500.00 |
| 4 | Jan 15, 2025 | Wed | Jan 15, 2025 | Wed | None | 0.2556 | $112,500.00 |
| 5 | Apr 15, 2025 | Tue | Apr 15, 2025 | Tue | None | 0.2500 | $112,500.00 |
| 6 | Jul 15, 2025 | Tue | Jul 15, 2025 | Tue | None | 0.2528 | $112,500.00 |
| 7 | Oct 15, 2025 | Wed | Oct 15, 2025 | Wed | None | 0.2556 | $112,500.00 |
| 8 | Jan 15, 2026 | Thu | Jan 15, 2026 | Thu | None | 0.2556 | $112,500.00 |

In this example, no adjustments were needed because the 15th didn't fall on a weekend for any quarter in 2024-2026. But consider a contract starting March 15, 2025 — the first quarterly payment on June 15, 2025 falls on a Sunday and would be adjusted to June 16 (Monday).

## IML Formal Model

The formal model in [`irs_scheduler.iml`](./irs_scheduler.iml) encodes dates as integers where `date mod 7` gives the day of the week. This abstraction captures the essential behavior of business day adjustment without the complexity of full calendar arithmetic.

The model defines:
- `adjust_following` — moves weekend dates forward to Monday
- `adjust_preceding` — moves weekend dates backward to Friday
- Three verification goals that prove properties about these functions

## Verification Results

| Property | Method | Result | Impact |
|----------|--------|--------|--------|
| No weekend dates | Formal proof | **PROVED** | All inputs covered |
| Naive monotonicity | Formal proof | **REFUTED** | Counterexample found |
| Practical monotonicity (7+ days) | Formal proof | **PROVED** | All swaps covered |

**VG1 — No weekend dates after adjustment (PROVED):** For any input date, `adjust_following` never produces a weekend date. This holds universally, not just for tested inputs.

**VG2 — Naive monotonicity (REFUTED):** The intuitive property "if d1 < d2 then adjust(d1) < adjust(d2)" is false. **Counterexample:** Saturday and Sunday are consecutive dates (d1 < d2), but both adjust to the same Monday. This means the strict ordering of dates is not preserved through business day adjustment. A naive implementation that assumes adjusted dates remain strictly ordered would contain a latent bug.

**VG3 — Practical monotonicity for 7+ day gaps (PROVED):** When dates are at least 7 days apart — which is always the case for swap payment schedules (monthly, quarterly, semi-annual, or annual) — strict ordering is preserved after adjustment. This guarantees that all real-world swap schedules maintain correct payment date ordering.

## Regulatory Context

Interest rate swap scheduling is subject to multiple regulatory frameworks:

- **EMIR (Europe):** Requires accurate trade reporting, margin calculations, and central clearing mandates for standardized OTC derivatives.
- **Dodd-Frank (US):** Mandates swap data repositories, real-time reporting, and risk mitigation procedures for swap dealers and major participants.
- **ISDA Definitions (2006):** The industry-standard legal framework defining business day conventions, day count methods, and payment calculation rules used in swap contracts worldwide.

Formal verification of scheduling logic provides evidence of correctness that supports compliance with these frameworks.

## Running the Demo

```bash
# Type-check the model
codelogician-lite check irs_scheduler.iml

# Run all 3 verification goals
codelogician-lite check-vg irs_scheduler.iml
```

## Source

Original case study: [codelogician.dev/docs/industry-case-studies/interest-rate-swap-schedule-generator](https://codelogician.dev/docs/industry-case-studies/interest-rate-swap-schedule-generator/)
