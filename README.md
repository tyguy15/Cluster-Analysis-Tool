# CNHP
# Cluster Analysis Machine

A toolbox for processing messy datasets of individual observations into meaningful, deduplicated biological occurrence records ready for bulk upload into Biotics (as SF geometry with visits).

---

## Prerequisites

Before running any tools, complete these manual steps:

1. Project data into **NAD83**
2. Run **Find Identical** on: `Shape` and `SElementID`, then join `FEAT_SEQ` back to the dataset
   - Input Field: `OBJECTID`
   - Join Field: `IN_FID`
   - Transfer Field: `FEAT_SEQ`

---

## Workflow

### Tool 1 — Add Sequential ID

A simple safety net. Before anything gets reshuffled, every record gets a stable sequential number (`AnotherID`) so you can always trace a record back to where it started, since ArcGIS OBJECTIDs can shift during processing. Can also rely on a unique ID from the dataset such as `observation_id` for iNat.

---

### Tool 2 — Near 9m Analysis

Finds nearby same-species pairs — *"Which observation points are within 9 meters of each other AND are the same species?"*

According to NatureServe methodology, occurrences of the same species within 9m of each other should be the same spatial occurrence (Source Feature). This step generates a Near Table of those pairs, ignoring self-matches and cross-species comparisons. This is the raw proximity evidence that feeds the grouping step.

---

### Tool 3 — Group into Occurrence Clusters (9m)

Takes those pairs and runs a graph analysis to form connected groups. If point A is near B, and B is near C, all three end up in the same group even if A and C aren't directly close to each other. The result is an `OccurrenceGroupID` assigned to every point — including isolated ones that had no neighbors.

Essentially groups records into clusters that may represent the same biological occurrence (based on NatureServe methodology).

> **Manual step:** Join the `OccurrenceGroupID` back to the dataset.

---

### Tool 4 — Occurrence Group Summary

Summarizes each occurrence group by calculating the number of unique locations and the maximum bounding diameter, then flags any groups exceeding a user-defined extent threshold. Flagged groups may represent biologically significant chain-clustering that warrants manual review (i.e. a stream reach or meadow better represented by a polygon or multiple points).

---

### Tool 5 — Choose Representative Point

Each occurrence group needs a single best geometry to represent it in the Biotics database (the Source Feature geometry). The script picks one record per group by first preferring the smallest buffer distance (most precisely located), then breaking ties by the most recent observation date. Everything else in the group gets flagged as non-representative and will become Visits to the Source Feature.

> **Manual step:** Select by attribute and create a new layer of **representative points only**. Run the next tool on only this layer.

---

### Tool 6 — Buffered Point Cluster Analysis

A coarser round of spatial grouping using each point's buffer distance (uncertainty) as the proximity rule rather than a fixed 9m threshold. Two points cluster together if the distance between them falls within either point's buffer radius, or if one contains the other. A cap of your chosen max prevents runaway merging across large distances. This assigns a `cluster_id` and handles flagging occurrences with lots of overlap due to larger buffer distances.

> **Manual step — choose one:**
> - Run **Summary Statistics** on `cluster_id` and join the `FREQUENCY` from the output table back to the point layer based on `cluster_id`
> - **OR** join the `cluster_id` to the representative points and run **Tool 4 – Occurrence Group Summary**, changing the output field names accordingly

Manually review these clusters to identify records with large uncertainty that are not necessarily spatially unique. Remove large records and/or assign them to an existing `OccurrenceID` and rerun this step until you reach a point where you are comfortable with the spatial redundancy of the occurrences (preferable to achieve as many `cluster FREQUENCY = 1` as possible).

You can select the corresponding visits of the representative points using a SQL query:
```sql
OccurrenceGroupID IN (SELECT OccurrenceGroupID FROM other_table)
```

---

### Tool 7 — Consolidate Visits and Concatenate Notes

Collapses duplicate visit records — observations by the same person on the same day at the same occurrence — down to one row per visit. It preserves the representative record where possible, collects all unique notes from the duplicates into a single concatenated field, and then deletes the redundant rows.


## Portions of this code were generated with the assistance of AI tools (Claude by Anthropic and ChatGPT by OpenAI).

