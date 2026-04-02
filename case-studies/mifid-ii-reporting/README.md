# MiFID II Transaction Reporting Classifier

**Discovering a jurisdictional bug where OTC trades between non-EEA entities were incorrectly flagged as reportable to ESMA.**

The original code checked only `instrument_region == EEA` for OTC trades without verifying counterparty locations, causing a US Hedge Fund buying BMW shares from a Singapore Bank over OTC to be reported to ESMA.

The model includes the fixed version with `has_eea_counterparty` check and a decomposition showing all 12 behavioral regions.

Source: [codelogician.dev/docs/industry-case-studies/mifid-ii-transaction-reporting-classifier](https://codelogician.dev/docs/industry-case-studies/mifid-ii-transaction-reporting-classifier/)

## Verification Results

| Goal | Result | What it proves |
|------|--------|----------------|
| Jurisdiction Safety: non-EEA OTC trades → not reportable | **PROVED** | Bug is fixed |
| Decomposition: `is_reportable` | **12 regions** | Complete behavioral coverage |

## Run it

```bash
# Type-check the model
codelogician-lite check mifid_reporting.iml

# Run the jurisdiction safety proof
codelogician-lite check-vg mifid_reporting.iml

# Run region decomposition (12 regions)
codelogician-lite check-decomp mifid_reporting.iml
```
