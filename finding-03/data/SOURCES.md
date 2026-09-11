# Data Sources

NHS England RTT Waiting Times: https://www.england.nhs.uk/statistics/statistical-work-areas/rtt-waiting-times/

The analysis uses the local manifest-listed RTT Incomplete Pathways CSVs. The local manifest records acquisition on 2026-07-17. No files were downloaded by this pipeline.
Vintages are classified from the local manifest: the six specified months are first release; the remaining months are revised unless the manifest notes otherwise.

| Period | Local filename | Manifest download URL | Vintage |
|---|---|---|---|
| 2024-01 | `202401-RTT-January2024-incomplete-pathways.csv` | (blank in local manifest; see NHS England base URL above) | Revised |
| 2024-02 | `202402-RTT-February2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/07/Full-CSV-data-file-Feb24-ZIP-3881K-revised.zip | Revised |
| 2024-03 | `202403-RTT-March2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2024/07/Full-CSV-data-file-Mar24-ZIP-3832K-revised.zip | Revised |
| 2024-04 | `202404-RTT-April2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/02/Full-CSV-data-file-Apr24-ZIP-4M-revised.zip | Revised |
| 2024-05 | `202405-RTT-May2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/02/Full-CSV-data-file-May24-ZIP-4M-revised.zip | Revised |
| 2024-06 | `202406-RTT-June2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/02/Full-CSV-data-file-Jun24-ZIP-4M-revised.zip | Revised |
| 2024-07 | `202407-RTT-July2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/02/Full-CSV-data-file-Jul24-ZIP-4M-revised.zip | Revised |
| 2024-08 | `202408-RTT-August2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/02/Full-CSV-data-file-Aug24-ZIP-4M-revised.zip | Revised |
| 2024-09 | `202409-RTT-September2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/02/Full-CSV-data-file-Sep24-ZIP-4M-revised.zip | Revised |
| 2024-10 | `202410-RTT-October2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/07/Full-CSV-data-file-Oct24-ZIP-4M-revised.zip | Revised |
| 2024-11 | `202411-RTT-November2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/07/Full-CSV-data-file-Nov24-ZIP-4M-revised.zip | Revised |
| 2024-12 | `202412-RTT-December2024-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/07/Full-CSV-data-file-Dec24-ZIP-4M-revised.zip | Revised |
| 2025-01 | `202501-RTT-January2025-incomplete-pathways.csv` | (blank in local manifest; see NHS England base URL above) | Revised |
| 2025-02 | `202502-RTT-February2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/07/Full-CSV-data-file-Feb25-ZIP-4M-revised.zip | Revised; analyst's local file verified against Apr-2026 reference; not re-downloaded (canonical URL recorded for provenance) |
| 2025-03 | `202503-RTT-March2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/07/Full-CSV-data-file-Mar25-ZIP-4M-revised.zip | Revised |
| 2025-04 | `202504-RTT-April2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/02/Full-CSV-data-file-Apr25-ZIP-4M-revised.zip | Revised |
| 2025-05 | `202505-RTT-May2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/02/Full-CSV-data-file-May25-ZIP-4M-revised.zip | Revised |
| 2025-06 | `202506-RTT-June2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/02/Full-CSV-data-file-Jun25-ZIP-4M-revised.zip | Revised |
| 2025-07 | `202507-RTT-July2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/02/Full-CSV-data-file-Jul25-ZIP-4M-revised-2.zip | Revised |
| 2025-08 | `202508-RTT-August2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/02/Full-CSV-data-file-Aug25-ZIP-4M-revised-2.zip | Revised |
| 2025-09 | `202509-RTT-September2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/02/Full-CSV-data-file-Sep25-ZIP-4M-revised.zip | Revised |
| 2025-10 | `202510-RTT-October2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2025/12/Full-CSV-data-file-Oct25-ZIP-4M-SrRW6y.zip | First release; first-release file (no revised version published as of 2026-07-17); NHS England typically posts revisions ~6 months later — re-pull in early 2027 for final figures |
| 2025-11 | `202511-RTT-November2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/01/Full-CSV-data-file-Nov25-ZIP-4M-1Xmjkk.zip | First release; first-release file (no revised version published as of 2026-07-17); NHS England typically posts revisions ~6 months later — re-pull in early 2027 for final figures |
| 2025-12 | `202512-RTT-December2025-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/07/Full-CSV-data-file-Dec25-ZIP-3M-revised.zip | Revised |
| 2026-01 | `202601-RTT-January2026-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/03/Full-CSV-data-file-Jan26-ZIP-4M-WL5BiP.zip | First release; first-release file (no revised version published as of 2026-07-17); NHS England typically posts revisions ~6 months later — re-pull in early 2027 for final figures |
| 2026-02 | `202602-RTT-February2026-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/04/Full-CSV-data-file-Feb26-ZIP-4M-9j03fJT.zip | First release; first-release file (no revised version published as of 2026-07-17); NHS England typically posts revisions ~6 months later — re-pull in early 2027 for final figures |
| 2026-03 | `202603-RTT-March2026-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/07/Full-CSV-data-file-Mar26-ZIP-3M-revised.zip | Revised |
| 2026-04 | `202604-RTT-April2026-incomplete-pathways.csv` | https://www.england.nhs.uk/statistics/wp-content/uploads/sites/2/2026/06/Full-CSV-data-file-Apr26-ZIP-3M-X7gGnn.zip | First release; analyst's local file verified against Apr-2026 reference; not re-downloaded (canonical URL recorded for provenance); first-release file (no revised version published as of 2026-07-17); NHS England typically posts revisions ~6 months later — re-pull in early 2027 for final figures |
| 2026-05 | `202605-RTT-May2026-incomplete-pathways.csv` | (blank in local manifest; see NHS England base URL above) | First release; first-release file (no revised version published as of 2026-07-17); NHS England typically posts revisions ~6 months later — re-pull in early 2027 for final figures |
