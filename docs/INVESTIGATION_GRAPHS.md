# Investigation OOS / OOT graphs

Open any investigation and choose **Analysis**, or use **View OOS / OOT graphs** on Overview. Both charts use the actual stored result and comparable historical records. No new measurements or fitted reference limits are fabricated.

## Specification graph

The OOS graph plots values in the result's unit against the linked specification version's lower and upper limits. A shaded band marks the stored interval; one-sided specifications show their available limit. A blue outline marks the case result. Point colors identify recorded OOS (red), OOT (amber), and other outcomes (blue). Equality with a specification boundary remains within the interval. The read model does not alter the recorded outcome or investigation.

## Baseline graph

The OOT graph plots signed `Z = (value − stored mean) / stored sigma` with the linked demo baseline's actual positive and negative Z threshold, its mean, sigma, version and baseline N. The baseline is not estimated from the case or chart window. A prior row linked to another baseline is left as a gap in the Z series rather than silently normalized to the case baseline.

A missing baseline, mismatched specification, unapproved profile, nonpositive sigma/threshold, or N below eight produces **OOT not assessed**, without invented Z-scores. OOS cases retain OOS precedence; their Z plot is labelled as context only. Stored demo bands are not a universal pharmaceutical OOT procedure or evidence of validation.

## Cohort and chronology

The bounded 20/40/80-result window uses the same tenant, site, material, test, unit and specification ID. The server permits at most 100 observations. Results are ordered by measurement time then result ID, ending at and always including the case result. Later measurement times and later IDs at the same measurement time are excluded. This is a measurement-history view, not a claim about which backdated records were available at investigation creation time.

The x-axis is an evenly spaced **chronological result sequence**, with UTC date labels; it does not represent equally spaced elapsed time. On narrow screens the plots scroll horizontally and initially reveal the case point at the right edge. A source-results table contains exact decimal values, signed Z-scores, UTC timestamps and source identifiers. The window counts are history counts; baseline N is separate stored metadata.

## API and validation

Authenticated endpoint: `GET /api/v1/workbench/events/{event_id}/analysis?limit=40`. Tenant/site authorization is checked before accessing case data. This change reads existing tables and requires no migration or reseeding.

Evidence: [OOS example](screenshots/investigation-oos-graphs.png), [OOT example](screenshots/investigation-oot-graphs.png), [mobile example](screenshots/investigation-graphs-mobile.png), and [validation record](INVESTIGATION_GRAPH_VALIDATION.json). The supplied examples use the synthetic demo dataset, not real manufacturer data.
