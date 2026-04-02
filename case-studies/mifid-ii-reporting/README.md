# MiFID II Transaction Reporting Classifier

## Overview

A jurisdictional bug in a regulatory reporting engine caused improper transaction reporting to ESMA (European Securities and Markets Authority). Formal verification with Codelogician discovers the over-reporting bug and proves the fix correct.

## The Problem

The Markets in Financial Instruments Directive II (MiFID II) requires investment firms operating in Europe to report certain trades to ESMA. The regulatory decision engine had a subtle jurisdictional flaw: it checked only the instrument's region without verifying whether either counterparty was actually European.

**Over-Reporting Risk:**
- Flooding regulators with irrelevant trades from non-EU jurisdictions
- Wasting compliance team bandwidth
- Exposing confidential trading strategies unnecessarily
- Legal liability for claiming authority over non-EU trades

**Under-Reporting Risk:**
- Missing mandatory disclosures to ESMA
- Regulatory fines up to EUR 5M or 10% of annual turnover
- Potential trading suspension or license revocation

## The Reporting Rules

The classifier follows a priority-based decision cascade:

| Priority | Question | Decision |
|----------|----------|----------|
| 1 | Did this trade happen on a European stock exchange? | REPORT |
| 2 | Is this a European instrument AND at least one party European? | REPORT |
| 3 | Was this an OTC trade AND at least one party European? | REPORT |
| 4 | None of the above? | DON'T REPORT |

## Original Python Implementation (Buggy)

```python
def is_reportable(trade: Trade) -> bool:
    # Priority 1: EEA Exchange
    if is_eea_exchange(trade.venue):
        return True

    # Priority 2: EEA Instrument - THE BUG
    if trade.instrument_region == Region.EEA:
        return True  # <- No counterparty check!

    # Priority 3: OTC with EEA Counterparty
    if trade.venue == Venue.OTC and has_eea_counterparty(trade):
        return True

    return False
```

Priority 2 is missing the counterparty check. Any trade involving a European instrument is flagged as reportable, even when neither party is European and the trade happened outside Europe.

## The Bug -- Counterexample

**The trade:**
- Buyer: US Hedge Fund (New York)
- Seller: Singapore Bank
- Instrument: BMW shares (German company)
- Venue: OTC (over the phone)

**The problem:** Neither party is European, the trade did not happen in Europe, and ESMA has no jurisdiction -- but the buggy code says "REPORT IT!" because `instrument_region == EEA` is true for BMW shares.

## The Jurisdiction Safety Property

Formal statement:

> For all trades t: (t.venue = OTC AND t.buyer_loc = NON_EEA AND t.seller_loc = NON_EEA) implies NOT is_reportable(t)

**Plain English:** An OTC trade between two non-European entities should never be reportable to ESMA, regardless of the financial instrument traded.

## Region Decomposition

The decomposition analysis partitions the input space into behavioral regions. Below is the simplified 8-region view showing how the fixed classifier handles every combination of inputs:

| # | Venue | Instrument Region | Buyer | Seller | Reportable? | Why |
|---|-------|-------------------|-------|--------|-------------|-----|
| 1 | EEA Exchange | Any | Any | Any | YES | Priority 1: trade on EU exchange |
| 2 | Non-EEA Exchange | EEA | EEA | Any | YES | Priority 2: EU instrument + EU party |
| 3 | Non-EEA Exchange | EEA | Non-EEA | EEA | YES | Priority 2: EU instrument + EU party |
| 4 | Non-EEA Exchange | EEA | Non-EEA | Non-EEA | NO | EU instrument but no EU party |
| 5 | Non-EEA Exchange | Non-EEA | Any | Any | NO | Non-EU instrument, non-EU exchange |
| 6 | OTC | Any | EEA | Any | YES | Priority 3: OTC + EU party |
| 7 | OTC | Any | Non-EEA | EEA | YES | Priority 3: OTC + EU party |
| 8 | OTC | Any | Non-EEA | Non-EEA | NO | OTC but no EU party (the fixed bug) |

Region 8 is where the bug lived: the buggy version returned YES for EEA instruments in this region, violating the jurisdiction safety property.

## IML Formal Model

The fixed model is in `mifid_reporting.iml`. It defines the trade types, the corrected `is_reportable` function, the jurisdiction safety property as a `verify` goal, and a decomposition of all behavioral regions.

Key fix in the IML model -- Priority 2 now requires `has_eea_counterparty`:

```
let is_reportable (t : trade) : bool =
  if is_eea_exchange t.venue then true
  else if t.instrument_region = EEA && has_eea_counterparty t then true
  else if t.venue = OTC && has_eea_counterparty t then true
  else false
```

## Verification Results

| Goal | Result | What it proves |
|------|--------|----------------|
| Jurisdiction Safety: non-EEA OTC trades -> not reportable | **PROVED** | Bug is fixed |
| Decomposition: `is_reportable` | **12 regions** | Complete behavioral coverage |

The full decomposition produces 12 regions (the table above shows a simplified 8-region view). The proof of the jurisdiction safety property confirms that no OTC trade between two non-EEA entities will ever be reported.

## Running the Demo

```bash
# Type-check the model
codelogician-lite check mifid_reporting.iml

# Run the jurisdiction safety proof
codelogician-lite check-vg mifid_reporting.iml

# Run region decomposition (12 regions)
codelogician-lite check-decomp mifid_reporting.iml
```

## Source

Original case study: [codelogician.dev/docs/industry-case-studies/mifid-ii-transaction-reporting-classifier](https://codelogician.dev/docs/industry-case-studies/mifid-ii-transaction-reporting-classifier/)
