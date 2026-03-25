# Tutorial: `codelogician eval` Command

The `eval` command evaluates IML (Imandra Modeling Language) code through ImandraX. The workflow has 3 stages: **check** (type-check), **verify** (prove/disprove properties), and **decompose** (partition input space + generate tests).

All example IML files are in the `iml/` directory.

## Prerequisites

Install CodeLogician and set your API key:

```bash
curl -fsSL https://codelogician.dev/codelogician/install.sh | sh
```

Get a free API key at [universe.imandra.ai](https://universe.imandra.ai) and export it:

```bash
export IMANDRA_UNI_KEY=your_key_here
```

---

## 0. What errors look like

Before diving in, here's what happens when IML code has problems. The CLI points directly at the issue with line/column locations.

**File: [`iml/errors.iml`](iml/errors.iml)** — contains both examples below, commented out. Uncomment one at a time and run `codelogician eval check iml/errors.iml` to see the errors yourself.

**Syntax error** — incomplete expression:

```iml
let bad (x : int) : int =
  if x > 0 then x else
```

```
Evaluation errors:

<error_1>
Lines: 3:2-3:3
Error: syntax error

  1 | let bad (x : int) : int =
  2 |   if x > 0 then x else
* 3 |
    |   ^
<kind>{ Kind.name = "SyntaxErr" }</kind>
</error_1>
```

**Type error** — mismatched types:

```iml
let add (x : int) (y : string) : int = x + y
```

```
Evaluation errors:

<error_1>
Lines: 1:40-1:44
Error: Application failed: expected argument of type `int`
but got (y : string)

* 1 | let add (x : int) (y : string) : int = x + y
    |                                         ^^^^
<kind>{ Kind.name = "TypeErr" }</kind>
</error_1>
```

When `check` succeeds, you'll see `Eval success!` — no news is good news.

---

## 1. `eval check` — Type-check and admit IML code

This is your first step. Always `check` before doing anything else.

**File: [`iml/basics.iml`](iml/basics.iml)**

```iml
let my_abs (x : int) : int =
  if x >= 0 then x else -x

let clamp (lo : int) (hi : int) (x : int) : int =
  if x < lo then lo
  else if x > hi then hi
  else x
```

**Command:**

```bash
codelogician eval check iml/basics.iml
```

This type-checks every definition. If there are errors, fix them and re-run. You can also pipe from stdin for quick experiments:

```bash
cat <<'EOF' | codelogician eval check -
let double (x : int) : int = x * 2
EOF
```

---

## 2. `eval list-vg` — List verification goals

After `check` succeeds, if your file contains `verify` or `instance` statements, list them to get their indices.

**File: [`iml/verify_abs.iml`](iml/verify_abs.iml)**

```iml
let my_abs (x : int) : int =
  if x >= 0 then x else -x

verify (fun x -> my_abs x >= 0)

verify (fun x -> my_abs x = x || my_abs x = -x)

instance (fun x -> my_abs x > 10)
```

**Command:**

```bash
codelogician eval list-vg iml/verify_abs.iml
```

This prints each goal with a 1-based index (1, 2, 3...) so you can target specific ones.

---

## 3. `eval check-vg` — Prove or find counterexamples

Run the actual verification. Use `--index N` to check a single goal, or `--check-all` for everything.

**Commands:**

```bash
# Check only the first goal (index 1): my_abs x >= 0
codelogician eval check-vg --index 1 iml/verify_abs.iml

# Check only the instance goal (index 3): find x where my_abs x > 10
codelogician eval check-vg --index 3 iml/verify_abs.iml

# Check all goals at once
codelogician eval check-vg --check-all iml/verify_abs.iml
```

**What you get back:**

- For `verify`: either **PROVEN** or a **COUNTEREXAMPLE** (concrete inputs that violate the property)
- For `instance`: a **concrete satisfying input** or a proof that none exists

---

## 4. `eval list-decomp` — List decomposition requests

If your file has `[@@decomp ...]` annotations, list them to get indices.

**File: [`iml/decomp_clamp.iml`](iml/decomp_clamp.iml)**

```iml
let clamp (lo : int) (hi : int) (x : int) : int =
  if x < lo then lo
  else if x > hi then hi
  else x
[@@decomp top ()]
```

**Command:**

```bash
codelogician eval list-decomp iml/decomp_clamp.iml
```

---

## 5. `eval check-decomp` — Run region decomposition

This partitions the function's input space into disjoint regions, each with constraints and a simplified invariant.

**Commands:**

```bash
# Check a specific decomposition by index
codelogician eval check-decomp --index 1 iml/decomp_clamp.iml

# Check all decompositions
codelogician eval check-decomp --check-all iml/decomp_clamp.iml
```

**What you get back:** A set of regions like:

- Region 1: `lo <= x && x <= hi` -> result is `x`
- Region 2: `x > hi` (with `lo <= x`) -> result is `hi`
- Region 3: `x < lo` -> result is `lo`

Each region includes a concrete model (example input satisfying the constraints).

### Decomposition with `~assuming`

**File: [`iml/decomp_discount.iml`](iml/decomp_discount.iml)**

```iml
type customer = { age : int; is_member : bool; total : real }

let valid c = c.age >= 0 && c.total >=. 0.0

let discount (c : customer) : real =
  if c.is_member then
    if c.age >= 65 then c.total *. 0.20
    else c.total *. 0.10
  else
    if c.age >= 65 then c.total *. 0.05
    else 0.0
[@@decomp top ~assuming:[%id valid] ()]
```

```bash
codelogician eval check iml/decomp_discount.iml        # type-check first
codelogician eval list-decomp iml/decomp_discount.iml   # see the decomp request
codelogician eval check-decomp --index 1 iml/decomp_discount.iml  # run it
```

This gives you 4 regions covering every branch of the discount logic, with concrete example customers for each.

---

## 6. `eval gen-test` — Generate test cases from decomposition

Once decomposition succeeds, generate executable test cases in Python or TypeScript.

**Commands:**

```bash
# Generate Python tests for the discount function
codelogician eval gen-test iml/decomp_discount.iml -f discount -l python

# Generate TypeScript tests, saving to a file
codelogician eval gen-test iml/decomp_discount.iml -f discount -l typescript -o discount_tests.ts

# Generate Python tests for clamp
codelogician eval gen-test iml/decomp_clamp.iml -f clamp -l python -o test_clamp.py
```

Each generated test corresponds to one region from the decomposition, with concrete input values and expected outputs.

---

## 7. Real-world example: Stripe payment flow

The [`../stripe/`](../stripe/) directory contains a complete worked example that takes a production Stripe payment processing flow through the full `eval` pipeline. It demonstrates how verification catches real bugs that code review and AI-generated tests miss.

### The model

The Python source (`stripe_payment_flow.py`, ~700 lines of Flask) is formalized as an IML state machine with 10 order statuses, 8 actions, and 7 transition functions:

```iml
type order_status =
  | Created | PaymentIntentCreated | RequiresAction | Authorized
  | ApprovedForCapture | Captured | PartiallyRefunded | Refunded
  | Disputed | Canceled

type order = {
  amount                : int;
  amount_captured       : int;
  amount_refunded       : int;
  status                : order_status;
  requires_review       : bool;
  high_risk             : bool;
  three_ds_required     : bool;
  three_ds_completed    : bool;
  approval_count        : int;
  payment_intent_exists : bool;
  latest_charge_exists  : bool;
}
```

A central `step` function dispatches actions to transition functions:

```iml
let step (a: action) (o: order) : order =
  match a with
  | ActCreatePaymentIntent -> create_payment_intent o
  | ActConfirmPaymentIntent -> confirm_payment_intent o
  | ActCompleteThreeDS -> complete_three_ds o
  | ActApproveForCapture -> approve_for_capture o
  | ActCapture amt -> capture_payment amt o
  | ActRefund amt -> refund_payment amt o
  | ActCancelPaymentIntent -> cancel_payment_intent o
  | ActOpenDispute -> open_dispute o
[@@decomp top ()]
```

### Try it yourself

All commands below assume you're in the `intro/` directory. Each command is self-contained — run them in order to walk through the full pipeline.

#### A. Type-check the original model (has a bug)

```bash
# Admit all definitions — should succeed with no errors
codelogician eval check ../stripe/stripe_flow_original.iml
```

#### B. Discover the bug via verification

```bash
# List all 10 verification goals with their indices (1-10)
codelogician eval list-vg ../stripe/stripe_flow_original.iml

# Check all VGs at once — 1 will be REFUTED
codelogician eval check-vg --check-all ../stripe/stripe_flow_original.iml
```

Or check specific goals individually:

```bash
# VG 1-4: amount invariants for create, confirm, 3DS, approve — all prove
codelogician eval check-vg --index 1 ../stripe/stripe_flow_original.iml
codelogician eval check-vg --index 2 ../stripe/stripe_flow_original.iml
codelogician eval check-vg --index 3 ../stripe/stripe_flow_original.iml
codelogician eval check-vg --index 4 ../stripe/stripe_flow_original.iml

# VG 5: amount invariant for capture — THIS ONE IS REFUTED
# Returns a counterexample where amount_refunded > amount_captured after re-capture
codelogician eval check-vg --index 5 ../stripe/stripe_flow_original.iml

# VG 6-7: amount invariants for refund, cancel — prove
codelogician eval check-vg --index 6 ../stripe/stripe_flow_original.iml
codelogician eval check-vg --index 7 ../stripe/stripe_flow_original.iml

# VG 8: no cancel after capture — proves
codelogician eval check-vg --index 8 ../stripe/stripe_flow_original.iml

# VG 9: no refund before capture — proves
codelogician eval check-vg --index 9 ../stripe/stripe_flow_original.iml

# VG 10: high-risk needs 2 approvals — proves
codelogician eval check-vg --index 10 ../stripe/stripe_flow_original.iml
```

The counterexample for VG 5 looks like:

```
amt = 1
o = {amount = 8957; amount_captured = 8957; amount_refunded = 1238;
     status = ApprovedForCapture; ...}
```

After capture: `amount_captured = 1` but `amount_refunded = 1238` — violating `amount_refunded <= amount_captured`. The fix: add `amount_refunded = 0` to the capture record update.

#### C. Type-check the fixed + extended model

```bash
# The updated model fixes the bug and adds 3DS + high-risk features
codelogician eval check ../stripe/stripe_flow_updated.iml
```

#### D. Verify all 14 goals on the fixed model

```bash
# List all 14 VGs (indices 1-14)
codelogician eval list-vg ../stripe/stripe_flow_updated.iml

# Check all at once — all 14 should prove
codelogician eval check-vg --check-all ../stripe/stripe_flow_updated.iml
```

Or explore specific goals by category:

```bash
# Amount-preservation invariants (VG 1-7, one per transition function)
codelogician eval check-vg --index 1 ../stripe/stripe_flow_updated.iml  # create
codelogician eval check-vg --index 2 ../stripe/stripe_flow_updated.iml  # confirm
codelogician eval check-vg --index 3 ../stripe/stripe_flow_updated.iml  # 3DS complete
codelogician eval check-vg --index 4 ../stripe/stripe_flow_updated.iml  # approve
codelogician eval check-vg --index 5 ../stripe/stripe_flow_updated.iml  # capture (now fixed!)
codelogician eval check-vg --index 6 ../stripe/stripe_flow_updated.iml  # refund
codelogician eval check-vg --index 7 ../stripe/stripe_flow_updated.iml  # cancel

# Base safety goals (VG 8-9)
codelogician eval check-vg --index 8 ../stripe/stripe_flow_updated.iml  # no cancel after capture
codelogician eval check-vg --index 9 ../stripe/stripe_flow_updated.iml  # no refund before capture

# 3DS feature goals (VG 10-11)
codelogician eval check-vg --index 10 ../stripe/stripe_flow_updated.iml # 3DS blocks authorization
codelogician eval check-vg --index 11 ../stripe/stripe_flow_updated.iml # 3DS completion authorizes

# High-risk / approval policy goals (VG 12-14)
codelogician eval check-vg --index 12 ../stripe/stripe_flow_updated.iml # high-risk needs 2 approvals
codelogician eval check-vg --index 13 ../stripe/stripe_flow_updated.iml # high-risk + 3DS requires both
codelogician eval check-vg --index 14 ../stripe/stripe_flow_updated.iml # review needs 1 approval
```

#### E. Region decomposition

```bash
# List decomp requests (1 decomp on the `step` function, index 1)
codelogician eval list-decomp ../stripe/stripe_flow_updated.iml

# Run the decomposition — discovers 84 disjoint execution paths
codelogician eval check-decomp --index 1 ../stripe/stripe_flow_updated.iml
```

The 84 regions cover every combination of `high_risk`, `requires_review`, `three_ds_required`, `three_ds_completed`, `approval_count` threshold, amount validity, and status — 53 for capture alone.

#### F. Generate test cases

```bash
# Generate Python tests from the decomposition (prints to stdout)
codelogician eval gen-test ../stripe/stripe_flow_updated.iml -f step -l python

# Save to a file instead
codelogician eval gen-test ../stripe/stripe_flow_updated.iml -f step -l python -o stripe_tests.py

# Or generate TypeScript
codelogician eval gen-test ../stripe/stripe_flow_updated.iml -f step -l typescript -o stripe_tests.ts
```

#### G. Run the generated tests against the Python implementation

```bash
cd ../stripe && python -m pytest test_stripe_flow.py -v  # 84/84 passed
```

#### H. Bonus: JSON output for programmatic use

Any `eval` subcommand (except `gen-test`) supports `--json`:

```bash
# Machine-readable VG results
codelogician eval check-vg --check-all --json ../stripe/stripe_flow_updated.iml

# Machine-readable decomposition
codelogician eval check-decomp --index 1 --json ../stripe/stripe_flow_updated.iml

# Machine-readable type-check
codelogician eval check --json ../stripe/stripe_flow_updated.iml
```

### Key files

| File | What it shows |
|------|---------------|
| `stripe_flow_original.iml` | Model with the bug — `check-vg` refutes 1 goal |
| `stripe_flow_updated.iml` | Fixed model + new features — 14/14 proved, 84 regions |
| `stripe_payment_flow.py` | Original Python source being formalized |
| `test_stripe_flow.py` | 84 pytest cases generated from decomposition |

### What this demonstrates

The `eval` pipeline isn't just for toy examples. On real business logic:

- **`check`** catches type-level mistakes early
- **`check-vg`** finds bugs that code review and AI-generated tests miss (the `amount_refunded` reset)
- **`check-vg`** also catches logically flawed properties (confusing "shouldn't change to X" with "output shouldn't be X")
- **`check-decomp`** exhaustively enumerates execution paths — 84 vs the ~10 a human or AI would guess
- **`gen-test`** turns those paths into runnable tests with concrete inputs and expected outputs

---

## End-to-end cheat sheet

Here's the full pipeline for a single file:

```bash
# Step 1: Type-check
codelogician eval check myfile.iml

# Step 2: List & run verification goals
codelogician eval list-vg myfile.iml
codelogician eval check-vg --check-all myfile.iml

# Step 3: List & run decompositions
codelogician eval list-decomp myfile.iml
codelogician eval check-decomp --check-all myfile.iml

# Step 4: Generate tests from decomposition
codelogician eval gen-test myfile.iml -f my_function -l python -o tests.py
```

Add `--json` to any command (except `gen-test`) for machine-readable output.
