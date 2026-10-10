# Technical notes

## Input and preparation

`secom.data` contains 1,567 space-delimited rows and 590 anonymous numeric fields; `NaN` means missing. `secom_labels.data` contains the corresponding outcome and quoted timestamp. Pair rows **before** sorting or filtering. `-1` means pass; `1` means fail. Timestamps parse with `dd/MM/yyyy HH:mm:ss` and an explicit `en-GB` culture. The timezone is unknown.

Power Query adds a one-based **Sample ID** from original row position. This is a technical key, not a factory device/lot identifier. Measurement names and IDs likewise preserve original column position. Source checks reject unexpected widths, label codes or mismatched row counts.

No rows, outliers or constant columns are removed. No measurements are imputed. The 33 repeated timestamps are retained; neither complete records nor measurement-only rows are exact duplicates. Reading storage omits null pairs; their absence remains explicit in denominators and detail labels.

All supplied numeric tokens have at most four decimal places. Fixed-decimal storage preserves these source values. Statistical means and variances explicitly convert to double precision **before aggregation** to avoid rounding small group differences to four decimals. A different source with more precision requires revisiting storage types.

## Data dictionary and relationships

| Table | Grain / key | Contents and use |
|---|---|---|
| Sample | One source row / Sample ID | Timestamp, date, outcome code, outcome and missing-measurement count; 1,567 rows. |
| Calendar | One calendar day / Date | Continuous 91-day range and Monday Week Start. Edge weeks are partial. |
| Measurement | One source column / Measurement ID | Neutral label, full-source status and shared histogram minimum/maximum; 590 rows. |
| Reading | One nonmissing Sample ID × Measurement ID | Original value and bin; 882,579 rows. |
| Measurement Selector | One measurement / Measurement ID | Disconnected single-measurement selection applied through `TREATAS`. |
| Histogram Bin | One bin / Bin | Disconnected integers 1–20. |
| Availability | One category / Status | Disconnected Available/Missing legend for sample detail. |

Relationships are one-to-many and single direction: Calendar → Sample → Reading; Measurement → Reading. A measurement filter does not propagate backwards into Sample and duplicate or shrink headline sample counts. The sample grain is unique, so `COUNTROWS(Sample)` is sufficient; counting rows of Reading would inflate outcomes.

The selector is disconnected to keep the exploratory ranking independent of the chosen measurement. Its measures apply `TREATAS` to Measurement. The ranking still responds to dates. Full-source measurement status and bin boundaries intentionally remain fixed across date selections.

## KPI definitions and filtering

| Measure | Definition / denominator |
|---|---|
| Samples | Sample rows in current dates/sample context, with Outcome and Outcome Code filters removed. |
| Passed / Failed Samples | Same context, applying the appropriate source outcome; zero for an observed period with no matching outcome. |
| Observed Pass / Failure Rate | Matching samples ÷ Samples. Empty periods return blank. Aggregate rates use counts, never averages of daily percentages. |
| Expected Readings | Current sample count × current measurement count. This measure honours outcome filters. |
| Valid Readings | Nonmissing Reading rows in current context. |
| Missing Readings | Expected minus valid readings. |
| Reading Completeness | Valid ÷ expected readings; blank without eligible samples. |
| Pass Valid / Fail Valid | Nonmissing readings for that outcome in current measurement/date context. |
| Reading Value / Status | Single sample and measurement evidence; missing rows retain a `Missing` status instead of becoming zero. |

Representative DAX:

```dax
Samples =
CALCULATE(
    COUNTROWS('Sample'),
    REMOVEFILTERS('Sample'[Outcome], 'Sample'[Outcome Code])
)

Observed Pass Rate = DIVIDE([Passed Samples], [Samples])

Reading Completeness = DIVIDE([Valid Readings], [Expected Readings])

Pass Mean =
CALCULATE(
    AVERAGEX('Reading', CONVERT('Reading'[Value], DOUBLE)),
    REMOVEFILTERS('Sample'[Outcome], 'Sample'[Outcome Code]),
    'Sample'[Outcome Code] = -1
)
```

Full documented measure expressions and Power Query partitions are in [`definition/tables`](../powerbi/SemiconductorQuality.SemanticModel/definition/tables). There is no hard-coded quality target. No period delta is shown: edge weeks are partial and daily coverage is uneven, so counts and rates are presented together.

## Measurement investigation

Group separation is the absolute difference between fail and pass means divided by their pooled sample standard deviation:

`|d| = |mean_fail − mean_pass| / sqrt(((n_pass−1) × variance_pass + (n_fail−1) × variance_fail) / (n_pass+n_fail−2))`

Only measurements with at least **100 valid pass readings**, **20 valid fail readings**, **80% coverage in each group** and a nonzero pooled standard deviation receive a score. The thresholds are analyst-selected screening rules, not industry standards. Means and sample variances use valid values only. Constants and insufficiently covered comparisons return blank.

The ranking is descriptive. It is not a p-value, causal attribution or predictive model, and it does not correct for searching many measurements. Correlated or redundant measurements can appear together. Extreme readings can affect means and standard deviations; they are retained because the source supplies no rule proving they are errors. Group medians are available in distribution tooltips.

Histograms use 20 equally spaced bins from each measurement's full-source minimum to maximum, shared across outcomes. Bins are left-inclusive/right-exclusive except the last bin, which includes the maximum. Constant measurements use bin 1. Each bar is the share of that group's **valid** readings, so different pass/fail sample sizes do not masquerade as distribution differences. Tooltips expose raw bin edges; no physical unit is invented. Outliers can compress the visible distribution—interpret the histogram with the scatter and medians.

The scatter displays elapsed fractional days from the first recorded timestamp and the selected original value. The tooltip retains the timestamp. Elapsed time is a derived display coordinate, not a source-provided process duration.

## Design and interaction

The 1920 × 1080 canvas uses a navy navigation rail, light background and white analytical surfaces. Blue identifies selection, teal passing outcomes, red failures and ochre missingness. Text and labels identify status independently of colour. Standard native visuals avoid custom-visual installations.

The overview's headline cards intentionally ignore chart and sample selections; the date slicer controls them. Other visuals can focus the sample browser on a week. On the measurement page, selecting a ranking row does not filter the other visuals—use the measurement dropdown. Date slicers are synchronized across the three main pages.

The reset bookmark is designed to restore all dates, Measurement 060 and no chart selections without changing the current page. The hidden Sample Detail page requires drillthrough from one Sample ID; opening it without a sample shows an explicit empty state. Its Back button returns to the source context. The measurement selector on detail narrows the reading table and coverage chart; the missing-count card remains the source sample's total.

## Verification

[`data-profile.json`](data-profile.json) records independent source counts, hashes, daily/weekly groups and all measurement profiles. Regenerate it with `python scripts/profile_secom.py`.

To reconcile the **open, refreshed Desktop model**, supply its current local Analysis Services port and installed Desktop `bin` directory:

```powershell
.\scripts\query_model.ps1 -Port <desktop-model-port> `
  -DesktopBin '<Power BI Desktop installation>\bin' `
  -OutputPath "$env:TEMP\secom-model-checks.json"
python scripts/validate_model.py "$env:TEMP\secom-model-checks.json"
```

The port changes between Desktop sessions. Find `msmdsrv.port.txt` in the active Desktop AnalysisServicesWorkspaces directory, or use a model inspection tool. Never assume a saved port is still current. The script uses Microsoft's locally installed ADOMD client for read-only DAX; no account or external service is involved. The raw query extract is temporary. Successful reconciliation writes a concise `model-validation.json` with tested scope, assertion count and measured query-batch time.

Checks include all 590 measurement means/counts/eligible scores, every recorded day and week, protected outcome denominators, empty selections, all 590 values for sample 1 including nulls, and four normalized histograms including a constant measurement. A numerical discrepancy discovered during development exposed premature fixed-decimal averaging; another exposed blank rates for zero-pass periods. Both are covered by source reconciliation.

On 9 October 2026, **5,874 assertions passed** against the refreshed Desktop model, including all 590 measurement comparisons. The final read-only query batch after refreshing the GitHub checkout took 0.257 seconds on the development machine (a single observed query run, not a refresh benchmark). See [model-validation.json](model-validation.json) for the exact scope and source hashes.

A full Import refresh from the configured local Data Folder took **85.46 seconds (1 minute 25 seconds)** after optimization, compared with the earlier **492.27 seconds (8 minutes 12 seconds)**. That is **82.64% less elapsed time** in these two local runs. A second full refresh from the final GitHub checkout took **79.49 seconds** and passed the same 5,874 measure checks. These are local observations, not a general performance guarantee. The full measure reconciliation passed after the optimized refresh. See [refresh-validation.json](refresh-validation.json).

An additional exhaustive check compared all **882,579 numeric readings** using decimal equality and verified the presence or absence of all **924,530 source positions**. All **41,951 missing positions** were preserved, no duplicate reading keys were found, and all **882,579 histogram bins** matched an independent calculation. All 39 DAX expressions are unchanged. See [reading-validation.json](reading-validation.json).

### Refresh changes

- The source reader uses Power Query's whitespace-aware CSV parser, with one buffered binary and a typed table per evaluation. This replaces nested text splitting and repeated conversion.
- Calendar reads only the small label file. Measurement Selector creates the schema's 590 identifiers directly, without rerunning measurement profiling.
- Each measurement's values are buffered as a list. Minimum and maximum determine constant/variable status, avoiding a distinct-value calculation.
- Reading builds numeric sample/measurement keys and histogram bins directly by measurement. It no longer unpivots a wide table into text labels and merges 882,579 rows with the profile table.
- Buffers are local to a query evaluation. The design does not claim a shared cache across independent Power Query queries.

Every refresh still reads the original files. There is no precomputed snapshot or hard-coded sample count in the import queries. Replacement input must retain SECOM's 590-field layout and row alignment with the label file. Missing fields, invalid outcome codes, row-count mismatches and readings beyond four-decimal precision cause an error instead of silent truncation or rounding. The file structure and precision requirements apply to other-company data too.

The Power Query definitions are stored in the [semantic model](../powerbi/SemiconductorQuality.SemanticModel/definition). Python is not required for an ordinary Power BI refresh.

To repeat the full-reading check after a refresh:

```powershell
.\scripts\export_readings.ps1 -Port <desktop-model-port> `
  -DesktopBin '<Power BI Desktop installation>\bin' `
  -OutputPath "$env:TEMP\secom-readings.csv"
python scripts/validate_readings.py "$env:TEMP\secom-readings.csv"
```

To refresh the data, select **Home > Refresh** in Power BI Desktop. The recorded refresh timings are retained in [refresh-validation.json](refresh-validation.json).

The authored report passed schema validation with zero errors and warnings. After Desktop saved its native version upgrades, the packaged copy had **zero errors and one schema-retrieval warning**: the public `visualContainer/2.13.0` schema could not be retrieved, so that schema check was skipped for 12 visuals. Their actual Desktop rendering was inspected successfully; the warning is not equivalent to complete schema coverage.

Drillthrough to Sample 1 and Back navigation were exercised successfully. A one-day date selection returned 12 samples, 9 passes, 3 failures and 75.00% observed pass rate. Selecting Measurement 001 returned 1,457 valid passes, 104 valid failures and a separation of 0.101. Reset restored all dates and Measurement 060 while preserving the six-row ranking and its order. All four screenshots, including the populated sample-detail page, were captured and inspected. The parameter configuration script was verified in an isolated copy, and local Markdown links resolved. Git staging preserved all three original source files byte for byte. Opening and refreshing a fresh clone on a second machine, and optional binary exports, have not been verified. Interaction latency was not instrumented; query-batch timing must not be presented as refresh or interaction latency.

## Reuse with another source

1. Preserve original source keys if they exist. Establish the actual grain (device, sample, lot or wafer); do not infer it.
2. Map the timestamp and documented outcome codes. Define retest treatment and whether first-pass yield is actually supported.
3. Adapt the ingestion functions and current 590-column checks to the new schema. Align records by a stable key where possible, rather than relying on position.
4. Map measurement identifiers, names, units and precision from genuine metadata. Review constant/missing profiles, count thresholds and histogram boundaries.
5. Reconcile totals, nulls, single-sample values and rates against an independent source calculation; verify interactions after refreshing.
6. Review performance for the expected volume. The detailed Reading table enables this report's sample-level exploration but can grow quickly. Larger deployments may need upstream transformations, aggregation or incremental refresh.

Equipment downtime, OEE, maintenance and specification capability require additional documented source tables and definitions. This project does not supply those metrics or pretend that a source-path change alone connects arbitrary company systems.

### Interaction fixes verified on 10 October 2026

The three full-source measurement counts now ignore report selections. Selecting Measurement 158 retains 474 variable, 116 constant and 0 all-missing measurements, while completeness correctly changes to 8.81%. Selecting Measurement 086 on 19 July 2008 now returns 0.00% completeness. Dates with no samples still return blank completeness. Only four DAX measures changed; source files and import queries were not changed.

Both cases were exercised in the reopened GitHub project in Power BI Desktop. Reset restored full-range completeness to 95.46%. The Data Quality and Measurement Investigation pages were captured and reviewed, and all 5,874 source-reconciliation assertions passed against the reopened model. The earlier statement that all 39 DAX expressions were unchanged applies to the refresh optimization, before these interaction fixes.
