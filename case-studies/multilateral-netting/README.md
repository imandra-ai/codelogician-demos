# Multilateral Netting Engine Verification

**Identifying critical bugs in a CCP multilateral netting engine.**

Two bugs found:
1. **No input validation** — negative amounts accepted, corrupting netting calculations
2. **Floating-point precision failure** (IEEE 754) causing phantom money ($473,040/year at 1,000 trades/second)

IML uses arbitrary-precision `real` arithmetic, eliminating the floating-point issue entirely. The model includes trade validation, net position calculation, zero-sum verification, and netting efficiency checks.

Source: [codelogician.dev/docs/industry-case-studies/multilateral-netting-engine-verification](https://codelogician.dev/docs/industry-case-studies/multilateral-netting-engine-verification/)

## Run it

```bash
# Type-check the model
codelogician-lite check multilateral_netting.iml
```
