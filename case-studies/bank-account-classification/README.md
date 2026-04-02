# Bank Account Classification Analysis

**Showing how a small code change dramatically increases behavioral complexity.**

Two versions of a transactional account classifier:
- **Basic** (167 lines): eligible product type + 3 inflows + 3 outflows → 19 behavioral regions
- **Enhanced** (203 lines): adds a balance threshold check → 55 behavioral regions

Code grew 21% but behavioral regions grew **190%**, demonstrating why formal analysis is essential — manual testing cannot keep up with combinatorial explosion.

Source: [codelogician.dev/docs/industry-case-studies/bank-account-classification-analysis](https://codelogician.dev/docs/industry-case-studies/bank-account-classification-analysis/)

## Files

| File | Description |
|------|-------------|
| `transactional_accounts_basic.iml` | Basic classifier: product + inflow/outflow counts |
| `transactional_accounts_enhanced.iml` | Enhanced: adds predicted balance threshold ($25M) |

## Run it

```bash
# Type-check both versions
codelogician-lite check transactional_accounts_basic.iml
codelogician-lite check transactional_accounts_enhanced.iml
```
