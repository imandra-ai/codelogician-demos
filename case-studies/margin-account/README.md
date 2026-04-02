# Margin Account Engine Verification

**Formal verification of a margin account state machine for institutional trading.**

Three account states: HEALTHY (equity ratio >= 50%), RESTRICTED (25% <= ratio < 50%), LIQUIDATION_CALL (ratio < 25%). References the Archegos Capital collapse ($10B+ losses).

Source: [codelogician.dev/docs/industry-case-studies/margin-account-engine-verification](https://codelogician.dev/docs/industry-case-studies/margin-account-engine-verification/)

## Verification Results

| Goal | Result | What it proves |
|------|--------|----------------|
| VG1: Solvency Safety — low equity ratio → LiquidationCall | **PROVED** | Status transitions are correct |
| VG2: Gap Risk — can withdrawal cause LiquidationCall? | **No counterexample** | Withdrawal guard prevents unsafe state |

## Run it

```bash
# Type-check the model
codelogician-lite check margin_account_engine.iml

# Run verification goals
codelogician-lite check-vg margin_account_engine.iml
```
