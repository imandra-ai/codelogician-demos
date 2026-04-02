# Algorithmic Trading Rules Analysis

## Overview

Complex trading rules with potential overlaps and redundancies. Formal verification detects unnecessary rules.

## The Problem

A complex algorithmic trading system has hundreds of business rules governing when and how trades can execute. These rules determine eligibility based on combinations of clients, algorithm types, and trading phases.

The core issue involves detecting redundant rules. Specifically, a special case rule exists for client XYZ that restricts `BENCHMARK_CLOSE_ONLY` algo types to the CLOSE trading phase. But does this rule actually do anything, or is it already covered by the general eligibility table?

Rather than testing all 108 combinations (9 clients x 6 algo types x 2 trading phases), formal verification can prove redundancy mathematically.

## Original Python Implementation

The trading system defines algorithm types, trading phases, and client identifiers:

```python
from enum import Enum
from dataclasses import dataclass

class AlgoType(Enum):
    BENCHMARK_TIME = 'benchmark time'
    BENCHMARK_VOLUME = 'benchmark volume'
    BENCHMARK_CLOSE = 'benchmark close'
    BENCHMARK_CLOSE_ONLY = 'benchmark close - close only'
    LIQUIDITY_SEEK_PASSIVE = 'liquidity seek - passive'
    LIQUIDITY_SEEK_AGGRESSIVE = 'liquidity seek - aggressive'

class TradingPhase(Enum):
    CONTINUOUS = 'Continuous'
    CLOSE = 'Close'

class ClientID(Enum):
    ABC = 'abc'
    DEF = 'def'
    XYZ = 'xyz'

def is_trading_phase_eligible_for_algo_type(
    algo_type: AlgoType,
    trading_phase: TradingPhase
) -> bool:
    """Check if a trading phase is eligible for an algo type."""
    eligibility_table = {
        AlgoType.BENCHMARK_TIME: {
            TradingPhase.CONTINUOUS: True,
            TradingPhase.CLOSE: True
        },
        AlgoType.BENCHMARK_CLOSE_ONLY: {
            TradingPhase.CONTINUOUS: False,
            TradingPhase.CLOSE: True
        },
    }
    return eligibility_table[algo_type][trading_phase]

def is_trading_phase_eligible_for_client_and_algo(
    client_id: ClientID,
    algo_type: AlgoType,
    trading_phase: TradingPhase
) -> bool:
    """Check eligibility for specific client and algo combination."""
    
    # ⚠️ Special rule for client XYZ
    if client_id == ClientID.XYZ and algo_type == AlgoType.BENCHMARK_CLOSE_ONLY:
        return trading_phase == TradingPhase.CLOSE
    
    return is_trading_phase_eligible_for_algo_type(algo_type, trading_phase)
```

To investigate whether the XYZ special case is redundant, we define a verification function:

```python
def verify_xyz_rule_is_redundant(
    client_id: ClientID,
    algo_type: AlgoType,
    trading_phase: TradingPhase
) -> bool:
    """Verify the special case produces identical results to the general rule."""
    if client_id == ClientID.XYZ and algo_type == AlgoType.BENCHMARK_CLOSE_ONLY:
        special_case_result = (trading_phase == TradingPhase.CLOSE)
        general_rule_result = is_trading_phase_eligible_for_algo_type(
            algo_type,
            trading_phase
        )
        return special_case_result == general_rule_result
    return True
```

## The Question

"Is this special case actually doing anything?"

`BENCHMARK_CLOSE_ONLY` already restricts **all** clients to the CLOSE phase only via the general eligibility table. The special rule for client XYZ enforces the exact same restriction. This makes the XYZ rule potentially redundant -- but how can we be certain without exhaustively checking every combination?

## IML Formal Model

The file `trading_rules.iml` models these trading rules in Imandra Modelling Language (IML) for formal verification. It encodes the algo types, trading phases, client identifiers, the general eligibility table, the client-specific rule, and verification goals that ask the prover to confirm the special case is redundant.

## Verification Results

| Goal | Result | What it proves |
|------|--------|----------------|
| VG1: `verify_xyz_rule_is_redundant` always returns true | **PROVED** | The special case is identical to the general rule |
| VG2: Client-specific = general for XYZ + BENCHMARK_CLOSE_ONLY | **PROVED** | Functions are mathematically equivalent |

The truth table confirms the result across all relevant inputs:

| Client | Algo Type | Trading Phase | Special Case | General Rule | Match |
|--------|-----------|---------------|--------------|--------------|-------|
| XYZ | BENCHMARK_CLOSE_ONLY | CONTINUOUS | False | False | ✓ |
| XYZ | BENCHMARK_CLOSE_ONLY | CLOSE | True | True | ✓ |
| ABC | BENCHMARK_CLOSE_ONLY | CONTINUOUS | False | False | ✓ |
| ABC | BENCHMARK_CLOSE_ONLY | CLOSE | True | True | ✓ |

## Recommended Refactoring

Since formal verification proves the special case is redundant, it can be safely removed. The simplified function:

```python
def is_trading_phase_eligible_for_client_and_algo(
    client_id: ClientID,
    algo_type: AlgoType,
    trading_phase: TradingPhase
) -> bool:
    return is_trading_phase_eligible_for_algo_type(
        algo_type,
        trading_phase
    )
```

## Key Insight

**Mathematical Certainty:** We didn't just test a few cases -- we proved for all possible values that the special case produces identical results to the general rule.

## Run it

```bash
# Type-check the model
codelogician-lite check trading_rules.iml

# Run both verification goals
codelogician-lite check-vg trading_rules.iml
```

## Source

Original case study: [codelogician.dev/docs/industry-case-studies/algorithmic-trading-rules-analysis](https://codelogician.dev/docs/industry-case-studies/algorithmic-trading-rules-analysis/)
