# 🔒 AGRI-DIRECT MVP — PROJECT FREEZE & CHANGE CONTROL

The following documents constitute the frozen source of truth for this 3–5 day internal hackathon MVP:

1. `AGRI-DIRECT-PRICING-ENGINE-V0.1-SPEC-FINAL.md`
2. `AgriDirect_Pricing_Engine_V0.1_AUDIT.md`
3. `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-SCOPE.md`
4. `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-STACK.md`
5. `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-ROADMAP.md`
6. `AGRI-DIRECT-PRICING-ENGINE-INTERNAL-MVP-ANTIGRAVITY-PROMPTS.md`

## FROZEN DECISIONS

The MVP scope, architecture, formulas, technology decisions, data contracts, deferred-feature boundaries, stage order, acceptance criteria, and testing requirements are FROZEN.

Do NOT:
- redesign the architecture;
- substitute technologies;
- introduce new frameworks;
- add deferred V0.1 features;
- remove required MVP features;
- alter the approved pricing formulas;
- alter the farmer-protection formula;
- alter the reliability formula;
- introduce a second pricing adjustment for demand/weather;
- silently change database semantics;
- silently change API contracts;
- silently expand the MVP scope.

The following are deliberate MVP decisions and MUST NOT be "improved" by replacing them:

- FastAPI directly serves the MVP frontend.
- Streamlit is the MVP frontend.
- PostgreSQL is required.
- PostGIS is deferred.
- Redis is deferred.
- Node.js is deferred.
- Prophet is deferred.
- HistGradientBoostingRegressor is the sole MVP ML model.
- Haversine distance is used instead of PostGIS.
- Demo-fixture fallback is mandatory.
- Synthetic/demo data must always be visibly identified as DEMO DATA.
- The MVP contains exactly five crops.
- The MVP covers one state and 5–10 mandis.
- The MVP implements the audit-corrected pricing formula.
- Weather and demand enter the model as features exactly once.

## CHANGE CONTROL

If implementation reveals a genuine contradiction, missing requirement, security issue, impossible dependency, or technical blocker:

1. STOP before changing the frozen decision.
2. Identify the exact affected document and section.
3. Explain the conflict.
4. Propose the smallest possible resolution.
5. Ask the developer for confirmation.
6. Do not silently rewrite the specification.

## IMPLEMENTATION FLEXIBILITY

The agent MAY make reasonable implementation decisions that do not alter frozen behavior, including:

- internal function/class organization;
- variable and module naming;
- minor UI styling;
- implementation refactoring;
- test organization;
- non-functional code improvements;
- equivalent implementation techniques;
- minor dependency patch-version adjustments when necessary for compatibility.

These changes must preserve the frozen architecture, behavior, formulas, interfaces, and scope.

## STAGE DISCIPLINE

Implement ONLY the current stage.

Do not pull future-stage features forward merely because they are convenient.

After implementation:
1. Run the required tests.
2. Run the full existing test suite.
3. Report every pass/failure.
4. Fix genuine implementation failures.
5. Verify previous-stage functionality remains intact.
6. Only then create the stage commit.

Do not skip, weaken, delete, or modify a test merely to obtain a passing result.

## PRIMARY OBJECTIVE

The goal is NOT to build the entire V0.1 system.

The goal is to deliver a reliable, explainable, professor-demo-ready internal MVP within 3–5 days that can later grow additively into V0.1.

When choosing between two valid implementation approaches, prefer the simpler approach that preserves the frozen architecture and reduces implementation risk.