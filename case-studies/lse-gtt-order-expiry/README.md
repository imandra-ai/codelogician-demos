# LSE GTT Order Expiry Verification

**Discovering a race condition in the London Stock Exchange trading system specification.**

GTT (Good Till Time) orders can expire simultaneously with auction uncross events, creating a compliance violation where orders are incorrectly excluded from auctions they should participate in.

MIT201 requirement: "Any GTT orders with an expiry time during any auction call phase will not be expired until after uncrossing has completed and are therefore eligible to participate in that uncrossing."

The model includes the fixed version (V2) that delays GTT expiry during auction until after uncross completes.

Source: [codelogician.dev/docs/industry-case-studies/lse-gtt-order-expiry-verification](https://codelogician.dev/docs/industry-case-studies/lse-gtt-order-expiry-verification/)

## Run it

```bash
# Type-check the model
codelogician-lite check lse_gtt_expiry.iml
```
