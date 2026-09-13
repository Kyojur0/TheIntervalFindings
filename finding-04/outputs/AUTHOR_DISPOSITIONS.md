# Author responses to the anomaly audit

Every finding and candidate has been reviewed. These are the developer/author's
responses to the separate anomaly agent; the audit files are preserved unchanged.
The monthly headline cohort and numerical results have not been retrospectively
recoded or imputed.

| Audit item | Author decision | Action and reason |
|---|---|---|
| A01 — total/detail duplication | Accepted; calculation corrected before the main build | National figures select the Total code once. Provider-level and national band reconciliation pass. The report explicitly corrects the doubled count in the brief. |
| A02 — blank bands | Accepted; certified-zero treatment retained | The parser rejects unresolved blanks. The independent raw scan corroborates every zero certificate; the compressed certificate log is retained. |
| A03 — RF4 gap | Accepted; reporting caveat added | The report identifies Barking, Havering and Redbridge's missing November submission and explains that the largest total fall partly reflects reporting absence. Counts are labelled submitted data. |
| A04 — RHQ absence | Accepted; reporting caveat added | Sheffield Teaching Hospitals' late-series absence is named in the report. No unknown band distribution is invented. |
| A05 — RA9 absence | Accepted; reporting caveat added | Torbay and South Devon's absence in the latest months is named. The declared scope and every chart state that missing-provider estimates are excluded. |
| A06 — RAP merger | Accepted; organisational explanation retained | The provider-presence record carries the documented acquisition. National sums retain each reported code once. The fixed-code sensitivity is explicitly not presented as a constant-service cohort. |
| A07 — coverage and names | Accepted; every case retained | All presence-event and name-change rows receive an explicit author response in `anomaly_candidate_dispositions.csv`. Known causes retain their sources; unknown causes remain unknown. Code-based pooling prevents duplicate rows arising from names. |
| A08 — possible specialty recodings | Accepted as candidates, not established causes | Every candidate receives a retained-as-reported disposition. The numerical screen is not sufficient to move pathways between specialties or identify individuals. The report includes a specialty-comparability caveat. |
| A09 — RJL coding break | Accepted; gastroenterology caveat added | The reported early gastroenterology baseline is retained. The report names the coding break and does not treat the general-medicine fall as an exact transfer to gastroenterology. |
| A10 — March distribution step | Accepted; values retained with limits | The same-provider and official-workbook checks corroborate the submitted distribution change. The report distinguishes the largest median move from the largest count move and does not claim to establish its cause or rule out revision effects. |
| A11 — other discontinuities and vintages | Accepted; release sensitivity and caveats retained | Observed-distribution thresholds are recorded. First-release exclusion is reported; common-provider persistence does not prove that revision effects are absent. No unsupported structural-break cause is asserted. |
| A12 — clean validity/schema/open-band checks | Accepted; evidence retained | Modern and historical schemas remain separate. The report restricts its open-band safety statement to the published pooled populations. |
| A13 — common endpoint providers | Accepted as a sensitivity result | The report states that improvement survives restricting the analysis to providers present at both endpoints. The separate cohort is labelled and is not mixed into headline figures. It cannot control merger footprint or service changes. |

The reviewer also identified the narrow code-prefix selection in the original
NHS workbook-method scan. The source note now names that selection explicitly,
and points out that the independent verifier includes the Other-service codes.
This changes the scope description of a check, not the estimator or reported
waiting-time values.

All candidate responses preserve the stable IDs and point to their original
evidence table. None is silently dropped. Where a cause is unknown, the response
is to retain the observation and caveat interpretation, not to claim a repair.
