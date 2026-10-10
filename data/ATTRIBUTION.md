# Source data

McCann, M. & Johnston, A. (2008). **SECOM** [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C54305

- Original source: https://archive.ics.uci.edu/dataset/179/secom
- Download: https://archive.ics.uci.edu/static/public/179/secom.zip
- Retrieved: 8 October 2026.
- License listed on the UCI source page: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).

`secom.data`, `secom_labels.data`, and `secom.names` are unmodified files extracted from the original archive. Checksums, sizes, and profiling results are recorded in `../docs/data-profile.json`; the redundant ZIP is not retained.

Measurement rows and label rows align by original position. Raw files contain 590 measurement columns, notwithstanding the original documentation's attribute-count discrepancy. Outcome -1 means pass; 1 means fail. Dates are day/month/year with no documented timezone. Nulls are encoded as NaN.

The source does not disclose the manufacturing company's identity, machine/lot identifiers, measurement meanings/units, retests, or downtime. Generated row indices are technical keys only. Source license and attribution must remain with reused data; any project-code license is separate. No source endorsement is implied.
