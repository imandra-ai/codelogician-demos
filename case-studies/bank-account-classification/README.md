# Bank Account Classification Analysis

## Overview

Simple feature addition creates exponential complexity growth. Region decomposition reveals behavioral expansion.

This demo uses two versions of a transactional account classifier -- basic and enhanced -- to show how a small code change (21% more lines) can produce a dramatic increase in behavioral complexity (190% more regions). Formal verification with IML makes this explosion visible and measurable.

## The Problem

Financial institutions must classify deposit accounts as "transactional" or "non-transactional" for:

- **Regulatory capital requirements** -- different capital buffers apply depending on account classification.
- **Interest calculations** -- transactional accounts often carry different rate structures.
- **Fee structures** -- account fees depend on the classification tier.
- **Customer eligibility** -- certain products and services are only available to transactional account holders.

Misclassification consequences:

- Regulatory non-compliance and penalties
- Incorrect risk assessments
- Customer complaints and reputational damage
- Revenue leakage

## Basic Classification Logic

An account qualifies as transactional if it meets **ALL** of the following criteria:

1. **Product Eligibility** -- The account's product type must be one of:
   - `Transaction`
   - `CMA_Direct`
   - `CMA_Platform`
   - `BB_Cheque_Account`
   - `BB_Regulated_Trust_Account`

2. **Active Use Test -- Inflows** -- At least 3 depositor-initiated inflows (credits) within the lookback period. Depositor-initiated transaction types include: Transfer, Direct_Debit, BPAY_Payment, Loan_Drawdown, Withdrawal, Deposit, RTGS_Payment, Cheque, Payment, Dividend, and Debit_Card.

3. **Active Use Test -- Outflows** -- At least 3 depositor-initiated outflows (debits) within the lookback period, using the same transaction type filter.

**Result: 19 Behavioral Regions**

## Enhanced Version

The enhanced version adds a predicted balance threshold check. The account type gains two new fields: `avg_30_day_balance` and `current_spot_interest_rate`. A predicted balance is computed as `avg_balance * (1 + interest_rate)` and compared against a $25M threshold (stored as 2,500,000,000 cents).

The new balance-related regions break down as follows:

1. **Zero Balance Regions** -- Balance = 0 automatically passes the threshold check.
2. **Below Threshold Regions** -- `predicted_balance <= $25M` -- account passes the threshold check.
3. **Exceeds Threshold Regions** -- `predicted_balance > $25M` -- account fails transactional classification regardless of product eligibility or active use.

An account now qualifies as transactional only when all three conditions hold: eligible product **AND** passed active use test **AND** predicted balance does not exceed the threshold.

**Result: 55 Behavioral Regions**

## The Key Finding: Complexity Explosion

Adding one simple balance check:

| Metric | Basic | Enhanced | Change |
|--------|-------|----------|--------|
| Lines of IML code | 153 | 171 | +21% |
| Behavioral regions | 19 | 55 | +190% |
| Test cases needed | ~19 | ~55 | 2.9x more |

> **"21% more code created 190% more complexity."**

This is the core insight: code size is a poor proxy for behavioral complexity. A single additional conditional branch, when combined with existing branches, multiplies the number of distinct execution paths. Manual testing strategies based on code coverage or line counts will systematically under-test the enhanced version.

## IML Formal Models

| File | Description |
|------|-------------|
| `transactional_accounts_basic.iml` | Basic classifier: product eligibility + inflow/outflow active use test |
| `transactional_accounts_enhanced.iml` | Enhanced classifier: adds predicted balance threshold ($25M) |

Both models define the full type system (product types, transaction types, debit/credit indicators, date handling), a recursive `count_flows` function that walks the transaction list, and a top-level `analyze_transactional_account` function that produces the classification result.

The enhanced model adds:
- `avg_30_day_balance` and `current_spot_interest_rate` fields to the `account` type
- `predicted_balance_outside_flag` field to the `analysis_result` type
- `check_predicted_balance_threshold` function
- A three-way pattern match (`eligible_flag, passed_active_use, predicted_balance_outside`) instead of a two-way match

## Verification Results

### Basic Version -- 19 Regions (sample)

| Region | Product Type | Inflows >= 3 | Outflows >= 3 | Result |
|--------|-------------|-------------|--------------|--------|
| 0 | Transaction | yes | yes | Transactional |
| 1 | CMA_Direct | yes | yes | Transactional |
| 2 | CMA_Platform | yes | yes | Transactional |
| 3 | BB_Cheque_Account | yes | yes | Transactional |
| 4 | BB_Regulated_Trust_Account | yes | yes | Transactional |
| 5 | Other | yes | yes | Not Transactional |
| 6 | Transaction | yes | no | Not Transactional |
| 7 | Transaction | no | yes | Not Transactional |
| 8 | Transaction | no | no | Not Transactional |

The 5 eligible product types each produce regions for the 4 inflow/outflow combinations (both pass, inflows only, outflows only, neither), minus shared "neither" regions. The `Other` product type fails regardless of active use.

### Enhanced Version -- 55 Regions

Each of the 19 basic regions is further split by the balance threshold condition (zero balance, below threshold, exceeds threshold), producing the 55-region total. Only accounts that are eligible, pass active use, AND have predicted balance at or below the threshold are classified as transactional.

## Running the Demo

```bash
# Type-check both versions
codelogician-lite check transactional_accounts_basic.iml
codelogician-lite check transactional_accounts_enhanced.iml
```

## Source

Original case study: [codelogician.dev/docs/industry-case-studies/bank-account-classification-analysis](https://codelogician.dev/docs/industry-case-studies/bank-account-classification-analysis/)
