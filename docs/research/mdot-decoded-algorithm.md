# MDOT Construction Density Calculator — Reverse-Engineered Algorithm

**Source**: `com.JacobArmour.ConstructionDensity` APK (Xamarin/C#)
**Decompiled**: 2026-02-21 from IL bytecode

---

## Constants

```
VOLUME_FACTOR = 16.0184633796014   // converts grams to pcf (1 / volume_cft / grams_per_lb)
                                    // = 1 / (0.0379 cft * 453.592 g/lb) ≈ recalc needed
INV_VOLUME = 1.0 / VOLUME_FACTOR   // ≈ 0.06243
```

## computeDensity(moisture, wetSoilG, isCone)

```csharp
double computeDensity(double moisture, double wetSoilG, bool isCone) {
    double volumeFactor = 16.0184633796014;
    double invVolume = 1.0 / volumeFactor;
    double wetDensity = wetSoilG * volumeFactor;  // wet density in some unit? No...

    // Wait - wetSoilG is in grams, volumeFactor converts to pcf
    // Actually: wetDensity = wetSoilG * (1 / (volume_cft * grams_per_lb))
    // But 16.018... = 62.4 * Gs? No. Let me reconsider...
    // 16.018 ≈ 1 / 0.06243 = 1 pcf in kg/m³ / some factor
    // Actually: 1 g/cm³ = 62.428 lb/ft³, so maybe unit conversion
    // wetSoilG * 16.018 seems too large...

    // Let me re-read: arg1 = moisture, arg2 = wetSoilG (but called with wetDensityPcf?)
    // The volumeFactor converts: wetSoilPcf = wetSoilLbs / volumeCft
    // If volume = 0.0379 cft and soil in grams:
    //   wetSoilLbs = wetSoilG / 453.592
    //   wetDensityPcf = wetSoilLbs / 0.0379 = wetSoilG / (453.592 * 0.0379)
    //   = wetSoilG / 17.191 = wetSoilG * 0.05817
    // But 16.018 ≠ 1/0.05817. Hmm.
    // Actually maybe the app passes wet density directly, not grams
    // wetDensity = wetSoilG * volumeFactor — this would be insanely large
    // OR: wetSoilG is already density and volumeFactor is 16.018 for unit conversion

    // Let me look at actual usage: the calculator UI has fields for
    // moisture, volume(cft), wet soil+mold(g), mold(g)
    // So wetSoilG = (wet+mold) - mold = wet soil weight in grams
    // Then the conversion would be:
    //   wetDensityPcf = wetSoilG / (volume_cft * 453.592)
    //   But that's division, not multiplication by 16.018

    // WAIT: 16.018463 = 1000 / 62.428 = kg/m³ per pcf
    // No: 62.428 lb/ft³ = 1 g/cm³ = 1000 kg/m³
    // So 1 lb/ft³ = 16.018 kg/m³
    // But that converts FROM pcf TO kg/m³, not useful here

    // Actually re-examining the IL more carefully:
    // arg1 = moisture (%), passed from UI
    // arg2 = some value, let me check what CalculateButton passes...
    // The CalculateButton calls computeDensity(moisture, ???, isCone)
    // arg2 is likely already wet density in pcf (pre-computed from UI inputs)

    // For now, the key insight is:
    // wetDensity_internal = arg2 * 16.018  (some internal unit)

    if (isCone) {
        if (coneTestValidate(moisture, wetDensity_internal)) {
            double dryDensity = coneDryDensity(moisture, wetDensity_internal);
            if (dryDensity > 0) {
                double optimumMoisture = coneOptimumMoisture(dryDensity);
                double mdd = dryDensity * invVolume;  // convert back
                RESULT_MDD = mdd;
                RESULT_OMC = optimumMoisture;
            }
        }
    } else {  // T-99
        if (t99TestValidate(moisture, wetDensity_internal)) {
            double dryDensity = t99GetDryDensity(moisture, wetDensity_internal);
            if (dryDensity > 0) {
                double optimumMoisture = t99GetOptimumMoisture(dryDensity);
                double mdd = dryDensity * invVolume;
                RESULT_MDD = mdd;
                RESULT_OMC = optimumMoisture;
            }
        }
    }
}
```

## t99GetOptimumMoisture(dryDensity)

**This is a closed-form polynomial!** Takes dry density (in internal units) and returns OMC%.

```
OMC = 1.513171926e-07 * dd^3
    - 0.001305844572 * dd^2
    + 4.46508485 * dd
    - 7584.68256
    + 6398417.7 / dd
    - 2084132642.0 / dd^2
    + 0.2
```

Where `dd` = dry density in internal units (pcf * 16.018)

Simplified: this is a rational polynomial in dd:
```
OMC(dd) = a3*dd³ + a2*dd² + a1*dd + a0 + a_neg1/dd + a_neg2/dd² + 0.2
```

Coefficients:
- a3 = 1.513171926e-07
- a2 = -0.001305844572
- a1 = 4.46508485
- a0 = -7584.68256
- a_{-1} = 6398417.7
- a_{-2} = -2084132642.0
- offset = +0.2

## t99GetDryDensity(moisture, wetDensity)

**This is a lookup table with linear interpolation!**

A 27x3 array where each row has 3 columns:
- col 0: slope (for the family curve line: line_y = slope * moisture + intercept)
- col 1: intercept
- col 2: boundary dry density value

The algorithm:
1. For each family curve i: compute `line_value = slope[i] * moisture + intercept[i]`
2. Find which two adjacent curves bracket the test point's wet density
3. Linearly interpolate the boundary dry density between those two curves

### T-99 Family Curve Table (27 rows)

| Row | Slope     | Intercept  | BoundaryDD |
|-----|-----------|------------|------------|
| 0   | 20.0233   | 1041.2106  | 1281.5     |
| 1   | 19.8326   | 1095.3688  | 1313.5     |
| 2   | 19.9391   | 1136.9451  | 1340.8     |
| 3   | 20.5864   | 1160.4782  | 1368.8     |
| 4   | 21.2323   | 1193.7296  | 1402.4     |
| 5   | 22.223    | 1235.0923  | 1442.5     |
| 6   | 16.7078   | 1430.4402  | 1480.1     |
| 7   | 23.2952   | 1336.5723  | 1526.6     |
| 8   | 24.5132   | 1360.9627  | 1561.8     |
| 9   | 26.5492   | 1376.8106  | 1601.9     |
| 10  | 29.3151   | 1383.9882  | 1648.3     |
| 11  | 32.3609   | 1398.798   | 1686.8     |
| 12  | 34.9099   | 1422.2762  | 1730.0     |
| 13  | 34.8573   | 1477.5005  | 1762.0     |
| 14  | 35.6593   | 1521.7693  | 1802.1     |
| 15  | 37.8552   | 1555.4084  | 1842.1     |
| 16  | 41.7427   | 1571.427   | 1880.6     |
| 17  | 43.6305   | 1606.668   | 1921.6     |
| 18  | 46.732    | 1625.8903  | 1954.3     |
| 19  | 52.0067   | 1641.909   | 1999.1     |
| 20  | 55.9757   | 1659.5294  | 2034.4     |
| 21  | 60.9041   | 1689.9648  | 2074.4     |
| 22  | 63.0395   | 1733.2151  | 2116.1     |
| 23  | 65.0395   | 1790.8822  | 2152.9     |
| 24  | 63.6689   | 1851.7529  | 2186.5     |
| 25  | 66.8011   | 1920.633   | 2234.6     |
| 26  | 67.8289   | 1986.3094  | 2266.6     |

### Converting BoundaryDD to pcf
BoundaryDD / 16.018 gives pcf:
- Row 0: 1281.5 / 16.018 = 80.0 pcf
- Row 26: 2266.6 / 16.018 = 141.5 pcf

So the table spans MDD from ~80 to ~141.5 pcf.

## t99TestValidate(moisture, wetDensity)

Validates that (moisture, wetDensity) falls within the chart bounds.

```csharp
bool t99TestValidate(double moisture, double wetDensity_internal) {
    if (wetDensity_internal < 1300.0 || wetDensity_internal > 2440.0) return false;

    double upperBound;
    if (moisture <= 24.0) {
        // Cubic polynomial for upper boundary
        upperBound = -0.033437479931 * m^3 + 2.521704131083 * m^2 - 82.275830523663 * m + 2872.3;
    } else {
        // Quadratic for high moisture
        upperBound = -1.09216780303 * m^2 + 43.710976287879 * m + 1458.5;
    }

    return wetDensity_internal <= upperBound;
}
```

## coneOptimumMoisture(dryDensity)

Cubic polynomial:
```
OMC = 1.194392432e-09 * dd^3 + 5.458657796e-06 * dd^2 - 0.052831877178 * dd + 84.758177133534
```

## coneDryDensity(moisture, wetDensity)

Same structure as t99GetDryDensity but with 21 rows.

### Cone Family Curve Table (21 rows)

| Row | Slope      | Intercept   | BoundaryDD   |
|-----|------------|-------------|--------------|
| 0   | 70.329387  | 2140.278864 | 2409.20105   |
| 1   | 67.39264   | 2096.837882 | 2362.74704   |
| 2   | 65.136956  | 2047.490712 | 2319.496755  |
| 3   | 59.315143  | 2021.346377 | 2269.839021  |
| 4   | 52.060528  | 2006.332656 | 2223.385011  |
| 5   | 45.193528  | 1996.826522 | 2176.931002  |
| 6   | 38.444698  | 1991.114963 | 2132.078854  |
| 7   | 31.417172  | 1993.457472 | 2087.226707  |
| 8   | 25.943565  | 1991.692955 | 2045.578285  |
| 9   | 23.221243  | 1966.458959 | 1999.124275  |
| 10  | 22.852605  | 1922.523974 | 1959.077715  |
| 11  | 21.857671  | 1880.483112 | 1915.82743   |
| 12  | 22.049599  | 1828.88395  | 1870.975283  |
| 13  | 21.209469  | 1790.78078  | 1829.326861  |
| 14  | 20.02328   | 1758.043984 | 1786.076576  |
| 15  | 19.466341  | 1720.172138 | 1747.631878  |
| 16  | 18.972578  | 1681.207873 | 1710.789043  |
| 17  | 18.48766   | 1645.684779 | 1675.54807   |
| 18  | 18.364932  | 1603.991458 | 1638.705235  |
| 19  | 18.257304  | 1561.482002 | 1603.464262  |
| 20  | 18.156393  | 1518.363492 | 1569.825152  |

### Cone BoundaryDD to pcf
- Row 0: 2409.2 / 16.018 = 150.4 pcf
- Row 20: 1569.8 / 16.018 = 98.0 pcf

## coneTestValidate(moisture, wetDensity)

```csharp
bool coneTestValidate(double moisture, double wetDensity_internal) {
    if (moisture < 5.0 || moisture > 20.0) return false;

    // Reciprocal polynomial upper boundary
    double upperBound = -2795547.646/m + 1557631.443/m^2 - 319202.5737/m^3
                        + 33028.87248188268/m^4 + 844.444613946511;

    // Wait, re-reading IL: it's nested divisions, not powers
    // Actually: (((-2795547.646/m + 1557631.443)/m - 319202.5737)/m + 33028.87)/m + 844.44
    // = -2795547.646/m + 1557631.443/m^2 ... no
    // Let me trace more carefully:
    // ldc -2795547.646 / m => A = -2795547.646/m
    // + 1557631.443 => B = A + 1557631.443
    // / m => C = B/m
    // - 319202.5737 => D = C - 319202.5737
    // / m => E = D/m
    // + 33028.87 => F = E + 33028.87
    // / m => G = F/m
    // + 844.44 => upperBound = G + 844.44

    // So: upperBound = (((-2795547.646/m + 1557631.443)/m - 319202.5737)/m + 33028.87)/m + 844.44

    return wetDensity_internal <= upperBound;
}
```

## Key Algorithm: How t99GetDryDensity Works

The family curves are straight lines in (moisture, wetDensity) space!

Each row defines a line: `wetDensity = slope * moisture + intercept`

Algorithm:
1. For each curve i (0 to 26), compute: `line_i = slope[i] * moisture + intercept[i]`
2. Find the first curve i where `line_i > wetDensity` (test point is below this curve)
3. The test point falls between curve i-1 and curve i
4. Linear interpolation:
   - `line_prev = slope[i-1] * moisture + intercept[i-1]`
   - `delta_line = line_i - line_prev`
   - `delta_boundary = boundary[i] - boundary[i-1]`
   - `fraction = (wetDensity - line_prev) / delta_line`
   - `dryDensity = boundary[i-1] + fraction * delta_boundary`
5. Then: `MDD = dryDensity / 16.018`

NOTE: Cone algorithm is identical but the comparison has a `+1.0` offset:
`line_i + 1.0 >= wetDensity` (cone uses `blt.s` after adding 1.0)

## Unit System

The internal unit factor 16.0184633796014 converts between pcf and what appears to be:
- 16.018 kg/m³ per lb/ft³ (standard conversion)
- So internal units are kg/m³ (SI)

All table values (slopes, intercepts, boundaries) are in kg/m³.
Input moisture is in % (passed through unchanged).
Output MDD = internal_dd / 16.018 = dd in pcf.
Output OMC = polynomial(internal_dd) = OMC in %.
