# LSE Stop Orders Verification

**Finding a critical bug where large orders bypass MIT201 safety rules.**

Validates Stop and Stop Limit orders per MIT201 Section 5.2. The original system had a bug where extended functionality for large orders (qty > 1000) bypassed all MIT201 rules, allowing both buy and sell stop orders to elect simultaneously.

This model uses the fixed version (no large-order bypass), but the verification goal still finds a counterexample showing both sides can elect — demonstrating that the simultaneous-election property is naturally violable when buy and sell stop prices bracket the LATP.

Source: [codelogician.dev/docs/industry-case-studies/lse-stop-orders-verification](https://codelogician.dev/docs/industry-case-studies/lse-stop-orders-verification/)

## Verification Results

| Goal | Result | What it shows |
|------|--------|---------------|
| No simultaneous election under valid state | **REFUTED** | Counterexample: LATP between buy_stop and sell_stop triggers both |

## Run it

```bash
# Type-check the model
codelogician-lite check lse_stop_orders.iml

# Run the verification goal (will produce a counterexample)
codelogician-lite check-vg lse_stop_orders.iml
```
