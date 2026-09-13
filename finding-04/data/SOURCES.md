# Sources and scope

The source is NHS England's monthly consultant-led Referral to Treatment waiting
times collection, acquired in the supplied project on 17 July 2026. The pack uses
the held vintages; it does not silently refresh them from today's publication.

`source_inventory.csv` identifies every held CSV by relative source path, byte
size and SHA-256. `manifest.json` preserves the original acquisition record and
available archive URLs. A blank archive URL means the supplied manifest did not
retain one; use the linked annual publication page and the file identifier. An
archive URL points to the NHS full extract, whereas the held modern monthly CSVs
contain the selected incomplete rows. Hashes describe the held CSVs, not the ZIPs.
The original extracts are intentionally omitted from this pack.

Main series: reported pathways only, with no missing-provider estimates; exact
Part_2, non-English commissioner NONC excluded, national C_999
Total counted once and reconciled against detailed specialties. Baseline: separate
53-band schema. Completed flows: exact Part_1A/Part_1B, known waits only, same
England scope; unknown clock starts are excluded from percentile denominators.

The supplied first-release months are October and November 2025, January and
February 2026, and April and May 2026. They are identifiable in the derived data
and tested separately. Other months retain their supplied revised/established
vintages; January 2024's official incomplete workbook is not labelled revised.

## Official methodology and comparisons

- [RTT statistical guidance and band definitions](https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/rtt-statistics-user-guidance/)
- [January 2024 statistical press notice](https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/03/Jan24-RTT-SPN-Publication-PDF-437K.pdf)
- `official_nhs_percentiles.csv`: precise source workbook URLs, cells, values and
  publication vintages; see the corresponding comparison in `../outputs/`.
- `../outputs/method_source_research.md`: evidence identifying the current linear
  convention from NHS workbook bands/values, with limits stated explicitly.
- `rtt_trajectory_national.csv`: unchanged supplied Finding 02 output used only
  as a reconciliation target. Current measures are rebuilt from raw inputs.

The figure specification is an unchanged copy from the reviewed Finding 03 pack.
The images are newly generated from the current outputs.
