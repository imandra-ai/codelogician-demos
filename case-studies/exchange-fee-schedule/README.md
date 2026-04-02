# Exchange Fee Schedule Verification

**Formally verifying the London Stock Exchange Trading Services Price List (January 2025).**

Found 5 behavioral regions in the execution fee calculation (expected 2-3) and proved key invariants across all package/tier/security combinations.

Source: [codelogician.dev/docs/industry-case-studies/exchange-fee-schedule-verification](https://codelogician.dev/docs/industry-case-studies/exchange-fee-schedule-verification/)

## Verification Results

| Goal | Result | What it proves |
|------|--------|----------------|
| VG1: Penny Jump — IOC/FOK costs exactly 0.01 GBP more than DAY | **PROVED** | Entry charge difference is exactly 1 penny |
| VG2: LPS Zero-Fee — execution fee = 0 at LPS Tier 3 | **PROVED** | Top-tier liquidity providers pay no execution fee |

## Key Findings

- **Small Trade Penalty**: minimum charge floors create effective rates up to 24x higher than stated for small trades
- **5 behavioral regions** in `calculate_execution_fee` (decomposition reveals the full structure)

## Run it

```bash
# Type-check the model
codelogician-lite check lse_equity_fees.iml

# Run verification goals
codelogician-lite check-vg lse_equity_fees.iml

# Run region decomposition
codelogician-lite check-decomp lse_equity_fees.iml
```
