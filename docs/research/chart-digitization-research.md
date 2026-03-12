# One-Point Chart Digitization — Research Document

**Project**: Field Guide App (Construction Inspector)
**Started**: Session 419 (2026-02-21)
**Last Updated**: Session 423 (2026-02-21)
**Status**: ALGORITHM FULLY REVERSE-ENGINEERED from MDOT APK. Both T-99 and Cone charts decoded. Ready for Dart implementation.

---

## Problem Statement

MDOT Form 0582B requires inspectors to determine **Max Density (MDD)** and **Optimum Moisture Content (OMC)** from a single field compaction test using the one-point method. Currently, inspectors do this by manually reading the MDOT charts (T-99 for cohesive soils, Michigan Cone for granular soils). We want to replace the manual chart reading with an equation in the app.

**Inputs**: Moisture content (w%), wet density (gamma_wet pcf)
**Outputs**: Max Density (MDD pcf), Optimum Moisture (OMC %)

---

## MDOT Charts

### T-99 Chart (Cohesive Soils — Loss-by-Washing > 15%)
- Red chart, AASHTO T-99 compaction energy
- Valid moisture range: optimum to 4% below optimum
- Worked example: w=17.3%, gamma_wet=119.0 pcf -> MDD=103.4, OMC=19.6%

### Michigan Cone Chart (Granular Soils — Loss-by-Washing <= 15%)
- Blue chart, Michigan Cone compaction method
- Valid moisture range: 5.0% to optimum
- Worked example: w=7.3%, gamma_wet=122.5 pcf -> MDD=115.2, OMC=13.4%

### Chart Files
- T-99 high-res: `Pre-devolopment and brainstorming/Form Templates for export/T-99RED-MDOT-Chart.pdf`
- Cone high-res: `Pre-devolopment and brainstorming/Form Templates for export/CONEBLU-MDOT-Chart.pdf`
- MDOT Density Manual: `Pre-devolopment and brainstorming/Form Templates for export/Density-Testing-Inspection-Manual.pdf`

---

## Validation Data Source: MDOT "Construction Density" Calculator App

An Android app built by someone at MDOT that performs the one-point calculation. No settings — single unified interface. This is our ground truth oracle.

**CRITICAL FINDING**: The calculator implements the **T-99 chart only**. When fed the Cone chart worked example (w=7.3%, gamma_wet=122.5), it returns MDD=121.9, OMC=12.1 (NOT the Cone answer of 115.2/13.4). It returns the T-99 answer for all inputs.

**Confirmed**: T-99 gold example matches EXACTLY (MDD=103.4, OMC=19.6).

### Calculator Input Format
- Moisture (%)
- Volume Sample (cft) — typically 0.0379
- Wet Soil + Mold (g)
- Mold (g) — typically 2452

### Conversion
- Wet Soil (g) = (Wet Soil + Mold) - Mold
- Wet Soil (lbs) = Wet Soil (g) / 453.592
- gamma_wet (pcf) = Wet Soil (lbs) / Volume Sample (cft)
- gamma_d (pcf) = gamma_wet / (1 + w/100)

---

## Collected Ground Truth Data (14 points, all T-99)

Source: MDOT Construction Density calculator app, screenshots saved in:
`C:\Users\rseba\OneDrive\Desktop\Density App Outputs\`

### Complete Dataset

| ID | w (%) | gamma_wet (pcf) | gamma_d (pcf) | MDD (pcf) | OMC (%) | offset (w-OMC) | Source |
|----|-------|-----------------|---------------|-----------|---------|----------------|--------|
| 11 | 17.3 | 119.0 | 101.45 | 103.4 | 19.6 | -2.3 | GOLD (T-99 exact match) |
| E  | 5.8  | 123.9 | 117.11 | 127.0 | 10.3 | -4.5 | Calculator (user's earlier test) |
| 13 | 10.0 | 120.9 | 109.91 | 115.1 | 14.6 | -4.6 | Calculator |
| 12 | 7.3  | 122.6 | 114.26 | 121.9 | 12.1 | -4.8 | Calculator |
| 7  | 3.0  | 123.0 | 119.42 | 133.8 | 8.3  | -5.3 | Calculator |
| 3  | 5.0  | 119.2 | 113.52 | 125.3 | 10.9 | -5.9 | Calculator |
| 5  | 15.0 | 110.9 | 96.43  | 100.1 | 21.3 | -6.3 | Calculator |
| 4  | 10.0 | 111.7 | 101.55 | 108.7 | 17.2 | -7.2 | Calculator |
| 8  | 8.0  | 113.9 | 105.46 | 113.3 | 15.2 | -7.2 | Calculator |
| 9  | 12.0 | 107.6 | 96.07  | 102.0 | 20.3 | -8.3 | Calculator |
| 10 | 20.0 | 103.0 | 85.83  | 88.8  | 28.3 | -8.3 | Calculator |
| 2  | 7.3  | 108.9 | 101.49 | 110.7 | 16.3 | -9.0 | Calculator |
| 6  | 25.0 | 97.0  | 77.60  | 80.5  | 34.9 | -9.9 | Calculator |
| 1  | 17.3 | 100.0 | 85.25  | 89.3  | 28.0 | -10.7 | Calculator |

### Boundary Curve Points (MDD vs OMC, sorted)
These are the (MDD, OMC) pairs from the calculator — they define the line of optimums:

| MDD (pcf) | OMC (%) |
|-----------|---------|
| 80.5      | 34.9    |
| 88.8      | 28.3    |
| 89.3      | 28.0    |
| 100.1     | 21.3    |
| 102.0     | 20.3    |
| 103.4     | 19.6    |
| 108.7     | 17.2    |
| 110.7     | 16.3    |
| 113.3     | 15.2    |
| 115.1     | 14.6    |
| 121.9     | 12.1    |
| 125.3     | 10.9    |
| 127.0     | 10.3    |
| 133.8     | 8.3     |

### Original Hand-Extracted Boundary Data (from chart images — SUPERSEDED)
These were extracted by reading the chart PDFs. They are LESS accurate than the calculator data above.

**T-99 (hand-extracted — DO NOT USE for fitting)**:
MDD: [140, 135, 130, 125, 120, 115, 110, 105, 100, 95, 90, 85, 80]
OMC: [3.5, 5.0, 6.5, 8.5, 10.5, 13.0, 15.5, 18.0, 21.0, 24.0, 27.0, 30.5, 34.0]

**Cone (hand-extracted)**:
MDD: [150, 145, 140, 135, 130, 125, 120, 115, 110, 105, 100]
OMC: [5.0, 5.5, 6.2, 7.2, 8.2, 9.5, 11.0, 13.0, 15.0, 17.5, 20.0]

---

## Mathematical Models Tested

### Model 1: Parabolic with Constant Alpha
```
gamma_d = MDD * (1 - alpha * (w - OMC)^2)
```
- **RESULT: FAILED** — alpha varies 10x across data (0.00037 to 0.00383)
- Overcorrects severely at large offsets
- Parabola accelerates away from optimum; real curves flatten

### Model 2: Gaussian with Constant Alpha
```
gamma_d = MDD * exp(-alpha * (w - OMC)^2)
```
- **RESULT: FAILED** — same 10x alpha variation as parabolic
- Gaussian is slightly better at large offsets but not enough
- Alpha variation is essentially identical to parabolic

### Back-Calculated Alpha Values (proving constant alpha impossible)

| MDD   | offset | alpha_parabolic | alpha_gaussian |
|-------|--------|-----------------|----------------|
| 103.4 | -2.3   | 0.003566        | 0.003602       |
| 133.8 | -5.3   | 0.003826        | 0.004050       |
| 125.3 | -5.9   | 0.002702        | 0.002836       |
| 115.1 | -4.6   | 0.002131        | 0.002196       |
| 113.3 | -7.2   | 0.001335        | 0.001384       |
| 108.7 | -7.2   | 0.001269        | 0.001313       |
| 100.1 | -6.3   | 0.000923        | 0.000943       |
| 102.0 | -8.3   | 0.000844        | 0.000869       |
| 88.8  | -8.3   | 0.000485        | 0.000495       |
| 89.3  | -10.7  | 0.000396        | 0.000405       |
| 80.5  | -9.9   | 0.000368        | 0.000374       |

**Key insight**: Alpha depends on BOTH MDD and offset. At the same MDD (~102):
- offset=-2.3 -> alpha=0.003566
- offset=-8.3 -> alpha=0.000844
This 4x difference at the same MDD proves the correction function is NOT quadratic.

### Effective Correction Exponent Analysis
Fitting g(x) = 1 - alpha * |x|^n to pairs of data points at similar MDD:
- At MDD~102: effective n ≈ 0.88 (sublinear — correction grows SLOWER than linearly)
- At MDD~89: effective n ≈ 1.19

The correction is much gentler than any quadratic model predicts.

---

## Session 422 Breakthroughs: Saturation-Line Model

### BREAKTHROUGH 1: Boundary Curve = Constant Saturation Line

Using the standard soil mechanics equation with Gs=2.70, gamma_w=62.4 pcf:
```
S = Gs * w / (100 * (Gs * gamma_w / gamma_d - 1))
```

Computed degree of saturation at EVERY (MDD, OMC) pair from 14 ground truth data points:

| MDD (pcf) | OMC (%) | S_opt (%) |
|-----------|---------|-----------|
| 80.5      | 34.9    | 86.2      |
| 88.8      | 28.3    | 85.2      |
| 89.3      | 28.0    | 85.3      |
| 100.1     | 21.3    | 84.2      |
| 102.0     | 20.3    | 84.1      |
| 103.4     | 19.6    | 84.1      |
| 108.7     | 17.2    | 84.4      |
| 110.7     | 16.3    | 84.3      |
| 113.3     | 15.2    | 84.3      |
| 115.1     | 14.6    | 85.0      |
| 121.9     | 12.1    | 85.5      |
| 125.3     | 10.9    | 85.4      |
| 127.0     | 10.3    | 85.2      |
| 133.8     | 8.3     | 86.5      |

**S_opt = 85.0% mean, ±0.7% std dev** — essentially constant!

**Boundary curve equation (line of optimums)**:
```
MDD = Gs * gamma_w / (1 + Gs * OMC / (100 * S_opt))
    = 168.48 / (1 + 0.03176 * OMC)

Where: Gs = 2.70, gamma_w = 62.4 pcf, S_opt = 0.85
```

This is a physics-based equation that perfectly explains the (MDD, OMC) relationship.

### BREAKTHROUGH 2: Normalized Offset Correlates with gamma_d/MDD

The ratio gamma_d_test / MDD correlates cleanly with normalized offset (w - OMC)/OMC:

| ID | (w-OMC)/OMC | gamma_d/MDD |
|----|-------------|-------------|
| 11 | -0.117      | 0.981       |
| E  | -0.437      | 0.922       |
| 13 | -0.315      | 0.955       |
| 12 | -0.397      | 0.937       |
| 7  | -0.639      | 0.893       |
| 3  | -0.541      | 0.906       |
| 5  | -0.296      | 0.963       |
| 4  | -0.419      | 0.934       |
| 8  | -0.474      | 0.931       |
| 9  | -0.409      | 0.942       |
| 10 | -0.293      | 0.967       |
| 2  | -0.552      | 0.917       |
| 6  | -0.284      | 0.964       |
| 1  | -0.382      | 0.955       |

Approximate linear fit: `gamma_d/MDD = 1 + c * (w - OMC)/OMC` where c ≈ 0.15
Effective c varies from 0.11-0.18 (±13%) — much better than the 10x alpha variation.
Mean abs error with constant c=0.15: 0.8% of MDD.

### Proposed Algorithm (Saturation + Normalized-Offset Model)

Given inputs (w, gamma_wet):
1. Compute gamma_d = gamma_wet / (1 + w/100)
2. Solve for OMC using:
   ```
   gamma_d = [168.48 / (1 + 0.03176 * OMC)] * (1 - c * (OMC - w) / OMC)
   ```
   This is one nonlinear equation in one unknown (OMC). Solve by bisection.
3. Compute MDD = 168.48 / (1 + 0.03176 * OMC)

**Parameters to calibrate**: Gs (≈2.70), S_opt (≈0.85), c (≈0.15)

### Gold Example Verification
- Input: w=17.3, gamma_wet=119.0, gamma_d=101.45
- At OMC=19.6: MDD_pred=103.83, gamma_d_pred=101.97 (actual 101.45)
- Model predicts OMC≈20.1, MDD≈102.8 (vs actual 19.6, 103.4)
- Error: MDD off by ~0.6 pcf, OMC off by ~0.5% — near OK threshold

### What This Model Gets Right vs Wrong
**Right**: The boundary curve is nearly exact (physics-based, S=85%, Gs=2.70).
**Approximate**: The family curve shape (linear with constant c) has ~1-2% scatter.
**Unknown**: Whether c should vary with MDD (high-MDD soils have steeper dry sides).

### Key Remaining Questions
1. Can c be refined with more data? (Variable c = f(MDD) might reduce scatter)
2. Does the model work at extremes (MDD < 80 or MDD > 135)?
3. Is Gs exactly 2.70, or does the calculator use a slightly different value?
4. What S_opt does the Cone chart use? (Different compaction energy = different S_opt)

---

## MDOT Manual Analysis (Session 422)

Read MDOT Density Testing and Inspection Manual (2024 Edition), pages 14-32.

### Key Findings from Manual
- **No equations published** — procedure is entirely graphical chart reading
- **Charts created by Robert D. Miles, MDOT C&T Division, November 2002**
- **Michigan Test Method (MTM) 404** describes the one-point T-99 adaptation
- **One-Point T-99**: Michigan adaptation of AASHTO T-99 Method C Modified
- **One-Point Cone**: Michigan-specific for granular soils (loss-by-washing ≤ 15%)

### Chart Procedure (T-99, page 18)
1. Plot (w, gamma_wet) as point A
2. Follow family curves ("radial lines") upward to boundary → point B
3. Read MDD from boundary curve at B
4. Drop vertically from B to x-axis → read OMC at point C

### Chart Geometry
- **X-axis**: Moisture Content, Percent of Dry Weight
- **Y-axis**: Compacted Soil Wet (Wet Density), Pounds Per Cubic Foot
- **Diagonal lines**: Lines of constant dry density (labeled 80, 85, ..., 140 pcf)
- **Boundary curve**: Line of optimums connecting peaks of all compaction curves
- **Family curves**: Curved "radial" lines representing compaction curves for different soils
- Family curves are NOT straight lines (do not converge at a single focal point)
- Family curves are NOT lines of constant saturation (S varies from ~20-71% at test points)

### Cone Chart Differences
- Range: 100-150 pcf MDD, 5-20% moisture
- Cone chart has curve labeled "M-N" as the boundary
- Procedure identical to T-99 chart

---

## Web Research Findings (Session 422)

### AASHTO T-272 / Published Equations
- **No published closed-form equation found** for the one-point method
- AASHTO T-272 describes a field test procedure, not an equation
- The method is fundamentally graphical: compile lab data → draw family curves → read chart
- Different state DOTs maintain their own family of curves charts (INDOT Chapter 13, SCDOT SCT-29, Kentucky KM 512)

### Hilf's Rapid Method (1959)
- Different from one-point chart method — Hilf is about field QC without knowing moisture content
- Uses "converted wet density" to determine relative compaction
- Not applicable to our problem (we know moisture content)

### Key Papers Found
- INDOT "Earthworks Chapter 13: Family of Curves and the One-Point Proctor Procedures"
- SCDOT SCT-29: "Field Determination of Maximum Dry Density and Optimum Moisture"
- VulcanHammer: "The Line of Optimums Approach for Compaction"
- Pandian et al. 1997: Theoretical modelling of the compaction curve
- Multiple sources confirm: family of curves are **empirically compiled from regional soil data**, not from equations

### Saturation at Optimum — Literature Confirms
- The line of optimums typically falls at S = 80-90% for standard Proctor (T-99)
- Higher compaction energy → higher S_opt (Modified Proctor → S ≈ 90-95%)
- Our finding of S_opt ≈ 85% for T-99 is consistent with published literature

### Horpibulsuk Power-Function Model (2008-2009)
Proposed that w vs S on each side of optimum follows power functions:
```
Dry side:  w = A_d * S^(B_d)
Wet side:  w = A_w * S^(B_w)
```
Key finding: **B_d, B_w, and S_opt are mainly dependent on soil type**, not compaction energy.
This could explain why constant-alpha fails: the real relationship involves saturation physics, not simple parabolas.
**Sources**: [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S003808062030336X), [Springer](https://link.springer.com/article/10.1007/s40996-018-0098-z)

### AASHTO T-272 — Confirmed Graphical Only
AASHTO T-272 "Standard Method of Test for Family of Curves -- One-Point Method" explicitly says:
- If point doesn't fall on a curve: "draw a new curve through the plotted point, parallel and in character with the adjacent curves"
- This is human visual judgment, NOT a formula
**Sources**: [Idaho DOT FOP](https://apps.itd.idaho.gov/apps/manuals/QA/Archive/files/2013Jan/2013FILES/files/2013Jan/570/embankment/t272_wpr_12.pdf), [WSDOT Materials Manual](https://wsdot.wa.gov/publications/manuals/fulltext/m46-01/t272.pdf)

### Complete Equation Reference Table
| # | Equation | Use |
|---|----------|-----|
| 1 | `gamma_d = gamma_wet / (1 + w/100)` | Convert wet to dry density |
| 2 | `gamma_d = Gs * gamma_w / (1 + e)` | Fundamental definition |
| 3 | `e = w * Gs / S` | Phase relationship (w as decimal) |
| 4 | `gamma_d = Gs * gamma_w / (1 + w*Gs/S)` | Density at given saturation |
| 5 | `gamma_d_zav = Gs * gamma_w / (1 + w*Gs)` | Zero air voids (S=100%) |
| 6 | `S_opt = w_opt * Gs / e_opt` | Back-calculate S_opt |
| 7 | `MDD = Gs*gamma_w / (1 + Gs*OMC/(100*S_opt))` | Boundary curve (our discovery) |
| 8 | `gamma_d/MDD ≈ 1 - c*(OMC-w)/OMC` | Family curve shape (our discovery, c≈0.15) |

### Key Web Sources for Future Reference
- [MDOT T-99 Chart PDF](https://mdotjboss.state.mi.us/webforms/GetDocument.htm?fileName=T-99RED.pdf)
- [MDOT Cone Chart PDF](https://mdotjboss.state.mi.us/webforms/GetDocument.htm?fileName=CONEBLU.pdf)
- [MDOT Density Manual](https://www.michigan.gov/mdot/-/media/Project/Websites/MDOT/Business/Construction/Standard-Specifications-Construction/CFS-Manuals/Density-Testing-Inspection-Manual.pdf)
- [INDOT Earthworks Ch13 - Family of Curves](https://www.in.gov/indot/files/Earthworks_Chapter_13.pdf)
- [Ohio EPA - Best Fit Line of Optimums](https://dam.assets.ohio.gov/image/upload/epa.ohio.gov/Portals/34/document/guidance/gd_665.pdf)
- [BuRec EM-26 - Hilf Method](https://www.usbr.gov/tsc/techreferences/hydraulics_lab/pubs/EM/EM26.pdf)
- [USDA - Estimating Proctor Curve from Intrinsic Properties](https://www.ars.usda.gov/ARSUserFiles/30200525/92-371-J%20Estimating%20a%20Proctor%20Density%20Curve%20from%20Intrinsic%20Soil%20Properties.pdf)

---

## Models Previously Proposed (Sessions 419-421, now superseded)

### Model 3: Published AASHTO/ASTM Equation
- **RESULT: NO EQUATION EXISTS** — the method is graphical, not equation-based
- Different DOTs use empirically compiled family-of-curves charts

### Model 4: Variable Alpha = f(MDD)
- Superseded by the normalized-offset approach (Model 7)

### Model 5: Saturation-Based Physics Model
- **PARTIALLY CONFIRMED** — the boundary curve IS a constant-saturation line (S≈85%)
- Family curves are NOT constant-saturation lines
- Combined with normalized-offset model to create Model 7

### Model 6: Table Lookup with Interpolation
- **Still viable as fallback** — generate dense calculator data and interpolate
- Requires many more data points (user's preferred approach)

---

## Python Prototypes

All in `tools/` directory:

| File | Purpose | Status |
|------|---------|--------|
| `one_point_prototype.py` | Original polynomial fitting, solver comparison, sensitivity analysis | Complete |
| `one_point_prototype_v2.py` | Anchor points, boundary adjustments, alpha optimization, LOO CV | Complete |
| `one_point_validation.py` | 15-test validation suite (uses old chart-read expected values) | Complete but OBSOLETE — replace expected values with calculator data |

### Planned but Not Yet Built
| File | Purpose |
|------|---------|
| `one_point_harness.py` | Scorecard-based test harness modeled on extraction pipeline |

---

## Harness Design (Brainstormed, Not Implemented)

Modeled after the extraction pipeline scorecard system (`stage_trace_diagnostic_test.dart`).

### Stages
1. **BoundaryFit** — polynomial quality (R², max residual)
2. **AlphaCalibration** — how alpha was derived
3. **Solver** — convergence (bracket, iterations, precision)
4. **Result** — MDD/OMC vs expected
5. **Tolerance** — pass/fail check

### Status Thresholds
- **OK**: |MDD error| <= 0.5 pcf AND |OMC error| <= 0.5%
- **LOW**: |MDD error| <= 1.0 pcf AND |OMC error| <= 1.0%
- **BUG**: exceeds LOW thresholds

### Output
- Per-test item traces (like GT item traces in extraction scorecard)
- Aggregate scorecard table (Stage, Metric, Expected, Actual, %, Status)
- Multi-model comparison table
- **JSON fixture dumps** to `tools/chart_validation/results/YYYY-MM-DD_NNN_{model}.json`

---

## Session History

### Session 419 (2026-02-21)
- Downloaded MDOT charts, extracted boundary data points from chart PDFs
- Designed hybrid algorithm: polynomial boundary + parabolic correction + iterative solver
- Identified that polynomial interpolation error is the dominant accuracy issue

### Session 420 (2026-02-21)
- Built 3 Python prototypes
- Polynomial fits: T-99 degree 3, R²=0.99993; Cone degree 3, R²=0.99983
- Alpha values: T-99 α=0.005928 (optimized), physics α=0.003566
- Validation: 10/15 pass. Both gold examples pass. 5 T-99 far-from-optimum fail
- Root cause identified: optimized α overcorrects at large offsets

### Session 421 (2026-02-21)
- Brainstormed Gaussian model (Option A) as alternative to parabolic
- Designed scorecard-based harness modeled on extraction pipeline
- **KEY BREAKTHROUGH**: User provided MDOT "Construction Density" calculator app
- Collected 14 exact ground truth data points from the calculator
- **DISCOVERY 1**: Calculator uses T-99 chart only (confirmed by gold example match)
- **DISCOVERY 2**: Constant alpha is IMPOSSIBLE — varies 10x across data
- **DISCOVERY 3**: Neither parabolic NOR Gaussian with constant alpha can work
- **DISCOVERY 4**: Real correction is sublinear (exponent ~0.88), much gentler than quadratic
- **DECISION**: Research published equation (AASHTO/ASTM) before implementing any model

### Session 422 (2026-02-21)
- Read MDOT Density Manual pages 14-32 (T-99 + Cone procedures, charts, worked examples)
- Confirmed: **NO equations exist in the manual** — procedure is purely graphical
- Web research: searched AASHTO T-272, Hilf method, ASTM standards, state DOT procedures
- Confirmed: **NO published equation exists** — all DOTs use empirical family-of-curves charts
- **BREAKTHROUGH 1**: Line of optimums = constant saturation at S=85% with Gs=2.70 (±0.7%)
- **BREAKTHROUGH 2**: gamma_d/MDD correlates with normalized offset (w-OMC)/OMC, slope c≈0.15
- **MODEL 7**: Boundary (saturation) + family curve (normalized linear) = solvable system
- Gold example: MDD error ~0.6 pcf, OMC error ~0.5% — near OK threshold
- **DECISION**: Collect dense data points from calculator before parameter fitting

### Session 423 (2026-02-21) — ALGORITHM REVERSE-ENGINEERED
- Extracted MDOT "Construction Density" APK from user's phone via ADB
- APK is Xamarin/C# by Jacob Armour (`com.JacobArmour.ConstructionDensity`)
- Decompressed XALZ-compressed .NET assemblies from XABA blob using LZ4
- Disassembled IL bytecode for all 7 calculation methods
- **BREAKTHROUGH**: Algorithm is a **piecewise linear lookup table** with polynomial boundary, NOT a physics equation
- T-99: 27-row family curve table (slope, intercept, boundaryDD) + rational polynomial for OMC
- Cone: 21-row family curve table + cubic polynomial for OMC
- Internal units are kg/m^3 (factor = 16.0184633796014 = pcf-to-kg/m^3 conversion)
- **Verified 14/14 ground truth points**: max MDD error 0.08 pcf, max OMC error 0.06% (rounding only)
- **ALL previous model research (parabolic, Gaussian, saturation-line) is SUPERSEDED**
- Both T-99 AND Cone charts fully decoded — no more blockers
- Decoded algorithm saved to `tools/mdot-apk/decoded_algorithm.md`

---

## Blockers

### BLOCKER-9: ~~Insufficient Data Density~~ RESOLVED (Session 423)
**Resolution**: Algorithm reverse-engineered from APK. We have the EXACT lookup tables and polynomials. No approximation needed.

### BLOCKER-10: ~~Cone Chart Validation~~ RESOLVED (Session 423)
**Resolution**: Cone chart algorithm also decoded from APK — 21-row lookup table + cubic OMC polynomial. Calculator DOES implement Cone (discovered during decompilation).

---

## Implementation Plan (UPDATED — Post Reverse-Engineering)

Phases 1-3 (data collection, harness, calibration) are **NO LONGER NEEDED** since we have the exact algorithm.

### Phase 1: Dart Implementation (NEXT)
**Goal**: Port the exact reverse-engineered algorithm to Dart.

**File**: `lib/features/quantities/services/one_point_calculator.dart` (new)
```dart
class OnePointResult {
  final double maxDryDensity;  // MDD in pcf
  final double optimumMoisture; // OMC in %
  final ChartType chartType;   // t99 or cone
}

class OnePointCalculator {
  static OnePointResult calculateT99({
    required double moisturePercent,
    required double wetDensityPcf,
  });
  static OnePointResult calculateCone({
    required double moisturePercent,
    required double wetDensityPcf,
  });
}
```
Algorithm to port:
- 27-row T-99 lookup table + 21-row Cone lookup table (slope, intercept, boundaryDD)
- Linear interpolation between bracketing family curves
- Rational polynomial for T-99 OMC, cubic polynomial for Cone OMC
- Validation polynomials for bounds checking
- Internal unit factor: 16.0184633796014 (pcf ↔ kg/m^3)
- All constants in `tools/mdot-apk/decoded_algorithm.md`

**Tests**: `test/features/quantities/one_point_calculator_test.dart`
- 14 ground truth points from MDOT calculator (should match within 0.1 pcf / 0.1%)
- Boundary edge cases (min/max MDD, extreme moisture)
- Cone chart worked example from MDOT manual

### Phase 2: Integration into 0582B UI
Per 0582B UI Redesign plan (`.claude/plans/2026-02-21-0582b-ui-redesign.md`):
- User enters moisture % and wet density (or raw weights)
- App computes MDD/OMC automatically using exact MDOT algorithm
- User selects chart type (T-99 vs Cone) based on loss-by-washing
- Shows computed result — no confidence indicator needed (algorithm is exact)
- User can override if needed

### Dependencies
- Phase 1 is pure Dart, no external dependencies
- Phase 2 depends on Phase 1 + 0582B UI redesign plan

---

## References

- MDOT Density Testing Inspection Manual (PDF in project)
- AASHTO T-99: Standard Proctor compaction test
- AASHTO T-272: One-point method for maximum dry density (if it exists)
- ASTM D698: Standard Test Methods for Laboratory Compaction
- ASTM D1557: Modified effort compaction
- Calculator screenshots: `C:\Users\rseba\OneDrive\Desktop\Density App Outputs\`
