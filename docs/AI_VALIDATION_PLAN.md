# QualisIQ — scientific rules, AI roadmap and validation

## What is already real in code

- OOS: compare decimal result against the *effective, versioned* approved demo specification. This uses `value < lower` or `value > upper`; equality with the specification limit is in-spec.
- OOT (demonstration only): in-spec result's absolute Z score >3.0 against a seeded synthetic reference mean/sigma with N>=8 and a single baseline. Spec OOS takes priority. True OOT requires SOP-defined alert/action rules, product/method/timepoint-specific baselines, and justified model suitability. Do not apply a universal 3-sigma rule as a regulatory standard.
- Missing baseline: `OOT_NOT_ASSESSED`, never silently assert a negative OOT finding.
- Evidence assistant: returns factual source record IDs, specification reference and human-review checklist only. **No live LLM or retrieval index is included.**

## QualisIQ future AI layers

1. **Statistics first:** robust historical QC charts, process-control limits, temporal stability regression, heteroscedasticity tests, seasonal drifts, instrument/method stratification. Version and approve analytical plans.
2. **Anomaly scoring:** isolation forest or gradient boosting for unusual multivariate trends (lab, method, instrument, time, product) with explainability and calibrated precision. Model outputs are *triage aids*, not failures or batch-release decisions.
3. **Retrieval:** chunk approved SOP/method documents, instrument logs and approved prior investigations with checksums and ACL metadata; query scoped sources. Index document versions and invalidate superseded content.
4. **Hypothesis agent:** structured JSON of `{hypothesis, supporting_evidence_ids, opposing_evidence_ids, confidence_descriptor, required_human_checks}`. Do not invent chromatography data, signatures, lab observations or retest rationale.
5. **Investigation drafting:** produce traceable drafts, each statement grounded to cited evidence, with clear `DRAFT / AI-ASSISTED / UNVERIFIED` markers and reviewer-visible changes.
6. **Agent governance:** prompt injection barriers, allowlisted tools, no source modifications by AI, no autonomous retest orders, no batch release, immutable AI request/output log, evaluation set across plants and methods.

## Benchmark suite to implement before claiming any AI effectiveness

| Dimension | Metric | Test |
|---|---|---|
| OOS correctness | 100% spec decision on curated boundary tests | ± specification range and equal endpoints |
| OOT behavior | Sensitivity and false-positive rate at approved alert thresholds | Backtest independent labeled QC time series |
| Source lineage | 100% output cases trace to source system, method, specification version | Random sample of 1,000 results |
| Retrieval faithfulness | Statement-to-source citation precision | Expert-reviewed 200-case evaluation |
| Hallucination control | Unsupported causal assertion rate | Adversarial/incomplete evidence set |
| Operator safety | No unreviewed QA decisions, invalidation or result overwrites | Policy tests, role tests, negative tests |
| Performance | p95 response, queue latency, ingestion throughput | Locust/k6 and failure recovery |
| Governance | User and site isolation | Automated authorization test matrix |

## Real regulatory source register

- FDA May 2022 OOS guidance: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/investigating-out-specification-oos-test-results-pharmaceutical-production-level-2-revision
- 21 CFR 211.192 investigation: https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-J/section-211.192
- FDA Part 11 scope: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application
- MHRA 2018 GxP data integrity (updated webpage 2021): https://www.gov.uk/government/publications/guidance-on-gxp-data-integrity
- ICH Q9(R1): https://www.fda.gov/regulatory-information/search-fda-guidance-documents/q9r1-quality-risk-management

**The starter is not a validated regulated system.** Regulatory references are for engineering planning and do not constitute legal/regulatory approval.
