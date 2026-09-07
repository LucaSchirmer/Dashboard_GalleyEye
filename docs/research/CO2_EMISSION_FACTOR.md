# CO2 emission factor for simulated fuel savings

## Decision

FSAIR may convert its estimated aviation-fuel savings in litres to a simulated
direct-combustion CO2 effect using this versioned assumption:

| Field | Value |
|---|---|
| Assumption version | `icao-corsia-jet-a-direct-co2-v1` |
| Value | `2.528` |
| Unit | `kg CO2/L fuel` |
| Fuel basis | Conventional Jet-A/Jet-A1 (ICAO applies the same mass factor to TS-1 and No. 3 Jet) |
| Emissions boundary | Direct fuel-combustion CO2 only (tank-to-wake) |
| Normative source | ICAO Annex 16, Volume IV, second edition (July 2023), Part II, Chapter 2, 2.2.3 |
| Public source | ICAO CORSIA FAQ, questions 3.59-3.62, accessed 2026-08-31 |

The litre-based factor is transparently derived from two ICAO values:

```text
3.16 kg CO2/kg fuel x 0.8 kg fuel/L = 2.528 kg CO2/L fuel
```

ICAO specifies `3.16 kg CO2/kg fuel` for Jet-A, Jet-A1, TS-1, and No. 3 Jet,
and specifies `0.8 kg/L` as the standard density where fuel is recorded by
volume rather than mass. It also says that an operator should use actual fuel
density when available. FSAIR has no measured fuel or density input, so the
ICAO standard density is appropriate only as an explicit simulated planning
assumption. See [ICAO CORSIA FAQ, Q3.59-Q3.62](https://www.icao.int/sites/default/files/environmental-protection/CORSIA/CORSIA-FAQ.html).
ICAO identifies the underlying standard as Annex 16, Volume IV; the second
edition became applicable on 1 January 2024 ([ICAO CORSIA FAQ, Q3.2](https://www.icao.int/sites/default/files/environmental-protection/CORSIA/CORSIA-FAQ.html)).

## Scope boundary

The result represents CO2 formed from combustion of the estimated saved fuel.
It is **not** a lifecycle or well-to-wake estimate and is **not** CO2-equivalent.
It excludes fuel extraction, refining, production, and distribution; CH4 and
N2O; NOx, contrails, and other non-CO2 aviation climate effects; and any
emissions associated with catering production or disposal.

This boundary follows from ICAO's equation, `CO2 emissions = mass of fuel x
fuel conversion factor`, and from ICAO's separate treatment of lifecycle
values for eligible aviation fuels. ICAO defines those lifecycle values in
`gCO2e/MJ` and includes production, transport, combustion, land-use change,
and credits; none of those lifecycle components is introduced into the factor
selected here. See [ICAO's lifecycle-emissions methodology](https://www.icao.int/CORSIA/fuels-lifecycle).

Accordingly, UI and export labels should say **simulated planning estimate of
direct fuel-combustion CO2 effect**. They must not call it measured or realized
emissions reduction, avoided lifecycle emissions, or climate impact.

## Academic cross-check

The ICAO value is consistent with the IPCC's fuel-carbon method. The *2006
IPCC Guidelines for National Greenhouse Gas Inventories*, Volume 2, Chapter 3,
Table 3.6.4 gives jet kerosene `71,500 kg CO2/TJ`; Volume 2, Chapter 1, Table
1.2 gives a net calorific value of `44.1 TJ/Gg`. Their product is `3.15315 kg
CO2/kg fuel`, consistent with ICAO's globally adopted `3.16 kg CO2/kg fuel`.
The implementation should nevertheless use the exact ICAO factor rather than
the independently derived IPCC cross-check.

- [IPCC 2006 Guidelines, Volume 2, Chapter 3, Table 3.6.4 (printed page 3.64)](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_3_Ch3_Mobile_Combustion.pdf)
- [IPCC 2006 Guidelines, Volume 2, Chapter 1, Table 1.2](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_1_Ch1_Introduction.pdf)

## Applicability limits

- Apply the factor only to FSAIR's estimated fuel saving in litres, after the
  direction-specific `L/kg carried` calculation. The emissions factor itself
  is global, not direction-specific; combustion chemistry does not change with
  route direction.
- The factor assumes conventional Jet-A/Jet-A1. It does not model a particular
  sustainable aviation fuel blend or its lifecycle benefit.
- AvGas and Jet-B are out of scope. ICAO specifies a different mass factor for
  those fuels, so silently applying `2.528 kg CO2/L` would be invalid.
- Preserve the unrounded value in calculations and round only for display or
  export according to the project's documented precision rule.
