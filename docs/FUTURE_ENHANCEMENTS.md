# Future Enhancements

These ideas are outside the first implementation's acceptance criteria. Reassess their evidence, data contracts, and privacy impact before implementation.

## Model-evidence drill-down

Show selected Consumption Images, reusable Reference Images, segmentation overlays, and Consumption Estimates for an item. Keep operational decision support separate from formal model evaluation.

## External data ingestion

Allow validated CSV uploads or connect to catering and flight-operation systems. Preserve the current five-table semantic contract and add provenance, versioning, and partial-observation handling before accepting real data.

## Historical analysis

Add longer time ranges, richer Comparable Flight Group definitions, trend analysis, seasonality, cabin class, aircraft type, flight duration, and service type. Require enough flights to support those additional dimensions.

## Recommendation review workflow

Let Catering Planners accept, reject, annotate, and revisit suggestions. This requires identity, persistence, audit history, and an explicit approval boundary.

## Reports and additional clients

Add PDF reporting and mobile-specific presentation only after the desktop workflow is stable.

## Item review signals

With sufficient repeated evidence, flag items for human review when they are both rarely selected when offered and poorly consumed. Phrase this as a signal, not proof of passenger dislike; account for service context, availability, and model uncertainty.

