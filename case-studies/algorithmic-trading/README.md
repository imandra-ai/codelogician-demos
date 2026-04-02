# Algorithmic Trading Rules Analysis

**Detecting redundant business rules through formal verification.**

A trading system has hundreds of business rules. A special rule for client XYZ with `BENCHMARK_CLOSE_ONLY` appeared to restrict trading to the CLOSE phase, but the base rule already enforced this for all clients. Rather than testing 108 combinations (9 clients x 6 algo types x 2 trading phases), formal verification proves redundancy mathematically.

Source: [codelogician.dev/docs/industry-case-studies/algorithmic-trading-rules-analysis](https://codelogician.dev/docs/industry-case-studies/algorithmic-trading-rules-analysis/)

## Verification Results

| Goal | Result | What it proves |
|------|--------|----------------|
| VG1: `verify_xyz_rule_is_redundant` always returns true | **PROVED** | The special case is identical to the general rule |
| VG2: Client-specific = general for XYZ + BENCHMARK_CLOSE_ONLY | **PROVED** | Functions are mathematically equivalent |

The special case can be safely removed.

## Run it

```bash
# Type-check the model
codelogician-lite check trading_rules.iml

# Run both verification goals
codelogician-lite check-vg trading_rules.iml
```
