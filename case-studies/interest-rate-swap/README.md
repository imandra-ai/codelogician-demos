# Interest Rate Swap Schedule Generator

**Formal verification of date calculation logic for IRS ($400+ trillion notional outstanding globally).**

Proves weekend payments are impossible and discovers edge cases in date monotonicity — consecutive weekend dates can collapse to the same Monday after business day adjustment.

Source: [codelogician.dev/docs/industry-case-studies/interest-rate-swap-schedule-generator](https://codelogician.dev/docs/industry-case-studies/interest-rate-swap-schedule-generator/)

## Verification Results

| Goal | Result | What it proves |
|------|--------|----------------|
| VG1: No weekend dates after adjustment | **PROVED** | `adjust_following` never produces a weekend |
| VG2: Naive monotonicity (d1 < d2 → adj(d1) < adj(d2)) | **REFUTED** | Consecutive weekend dates collapse to same Monday |
| VG3: Practical monotonicity (7+ day gaps) | **PROVED** | Safe for typical swap scheduling intervals |

## Run it

```bash
# Type-check the model
codelogician-lite check irs_scheduler.iml

# Run all 3 verification goals
codelogician-lite check-vg irs_scheduler.iml
```
