import arcpy
import math
from collections import defaultdict

def execute(parameters, messages):
    fc                = parameters[0].valueAsText
    occ_field         = parameters[1].valueAsText
    seed_id_field     = parameters[2].valueAsText
    extent_threshold  = parameters[3].value   # meters, user defined
    point_count_field = parameters[4].valueAsText
    diameter_field    = parameters[5].valueAsText
    flag_field        = parameters[6].valueAsText

    arcpy.env.overwriteOutput = True

    # -------------------------
    # STEP 1 — Add or reset output fields
    # -------------------------
    arcpy.AddMessage("Checking and preparing output fields...")
    existing = [f.name for f in arcpy.ListFields(fc)]

    if point_count_field not in existing:
        arcpy.management.AddField(fc, point_count_field, "LONG")
        arcpy.AddMessage(f"Added field: '{point_count_field}'.")

    if diameter_field not in existing:
        arcpy.management.AddField(fc, diameter_field, "DOUBLE")
        arcpy.AddMessage(f"Added field: '{diameter_field}'.")

    if flag_field not in existing:
        arcpy.management.AddField(fc, flag_field, "SHORT")
        arcpy.AddMessage(f"Added field: '{flag_field}'.")

    # Reset all flags and metrics to null/0 before calculating
    arcpy.management.CalculateField(fc, point_count_field, 0)
    arcpy.management.CalculateField(fc, diameter_field, 0)
    arcpy.management.CalculateField(fc, flag_field, 0)

    # -------------------------
    # STEP 2 — Read unique locations per occurrence group
    # We key on SeedID to count unique spatial positions,
    # not raw observation rows, so visit duplicates don't
    # inflate the point count
    # -------------------------
    arcpy.AddMessage("Reading occurrence groups and unique locations...")
    occ_seeds   = defaultdict(set)    # occ_id -> set of unique SeedIDs
    occ_coords  = defaultdict(list)   # occ_id -> list of (x, y) per unique SeedID

    seen_seeds = set()
    with arcpy.da.SearchCursor(
        fc, [occ_field, seed_id_field, "SHAPE@XY"]
    ) as cursor:
        for occ_id, seed_id, xy in cursor:
            if occ_id is None:
                continue
            occ_seeds[occ_id].add(seed_id)
            # Only record one coordinate per unique SeedID
            if seed_id not in seen_seeds:
                seen_seeds.add(seed_id)
                if xy is not None:
                    occ_coords[occ_id].append(xy)

    arcpy.AddMessage(f"Found {len(occ_seeds)} unique occurrence groups.")

    # -------------------------
    # STEP 3 — Calculate bounding diameter per group
    # Diameter = max pairwise distance between any two
    # unique locations in the group
    # For groups with only one unique location, diameter = 0
    # -------------------------
    arcpy.AddMessage("Calculating bounding diameters...")
    occ_diameter   = {}
    occ_pointcount = {}

    for occ_id, coords in occ_coords.items():
        point_count = len(occ_seeds[occ_id])
        occ_pointcount[occ_id] = point_count

        if len(coords) < 2:
            occ_diameter[occ_id] = 0.0
            continue

        # Calculate max pairwise distance
        max_dist = 0.0
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                dx   = coords[i][0] - coords[j][0]
                dy   = coords[i][1] - coords[j][1]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > max_dist:
                    max_dist = dist

        occ_diameter[occ_id] = round(max_dist, 2)

    # -------------------------
    # STEP 4 — Diagnostic summary
    # -------------------------
    flagged = {
        occ_id: d for occ_id, d in occ_diameter.items()
        if d > extent_threshold
    }
    arcpy.AddMessage(
        f"Occurrence groups exceeding {extent_threshold}m diameter: "
        f"{len(flagged)} of {len(occ_diameter)}"
    )
    if flagged:
        arcpy.AddMessage("Largest groups (top 5 by diameter):")
        for occ_id, diam in sorted(
            flagged.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            arcpy.AddMessage(
                f"  OccurrenceGroupID={occ_id} | "
                f"Diameter={diam}m | "
                f"Unique locations={occ_pointcount[occ_id]}"
            )

    # -------------------------
    # STEP 5 — Write metrics back to feature class
    # -------------------------
    arcpy.AddMessage("Writing metrics to feature class...")
    updated = 0

    with arcpy.da.UpdateCursor(
        fc, [occ_field, point_count_field, diameter_field, flag_field]
    ) as cursor:
        for occ_id, pt_count, diameter, flag in cursor:
            if occ_id is None:
                continue
            new_count    = occ_pointcount.get(occ_id, 0)
            new_diameter = occ_diameter.get(occ_id, 0.0)
            new_flag     = 1 if new_diameter > extent_threshold else 0
            cursor.updateRow((occ_id, new_count, new_diameter, new_flag))
            updated += 1

    arcpy.AddMessage(f"Updated {updated} rows.")
    arcpy.AddMessage("---------- COMPLETE ----------")
    arcpy.AddMessage(
        f"Fields written: '{point_count_field}', "
        f"'{diameter_field}', '{flag_field}'"
    )
    arcpy.AddMessage(
        f"{len(flagged)} occurrence groups flagged for review "
        f"(diameter > {extent_threshold}m)."
    )