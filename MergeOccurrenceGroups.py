import arcpy


def execute(parameters, messages):
    in_layer      = parameters[0].valueAsText
    group_field   = parameters[1].valueAsText
    species_field = parameters[2].valueAsText
    target_id     = parameters[3].value

    desc = arcpy.Describe(in_layer)

    # -------------------------
    # Read the selection: these are the representative points
    # you no longer want. Their whole groups will be relabeled.
    # -------------------------
    if not getattr(desc, "FIDSet", ""):
        raise ValueError(
            "No points are selected. Select the representative point(s) you "
            "no longer want, then run the tool again."
        )

    source_ids = set()
    with arcpy.da.SearchCursor(in_layer, [group_field]) as cursor:   # selected rows only
        for (gid,) in cursor:
            if gid is not None:
                source_ids.add(gid)

    if target_id in source_ids:
        arcpy.AddWarning(
            f"Group {target_id} is both selected and the target; skipping it."
        )
        source_ids.discard(target_id)

    if not source_ids:
        raise ValueError(
            "The selected points have no groups to merge into the target group."
        )

    # -------------------------
    # From here on, work on the full dataset (not just the selection)
    # -------------------------
    data   = desc.catalogPath
    delim  = arcpy.AddFieldDelimiters(data, group_field)
    id_list = ",".join(str(i) for i in sorted(source_ids))
    source_where = f"{delim} IN ({id_list})"
    target_where = f"{delim} = {target_id}"

    # Target group must exist
    species = set()
    target_count = 0
    with arcpy.da.SearchCursor(data, [species_field], target_where) as cursor:
        for (sp,) in cursor:
            species.add(sp)
            target_count += 1
    if target_count == 0:
        raise ValueError(f"Target group {target_id} was not found in {group_field}.")

    # Never merge different species
    with arcpy.da.SearchCursor(data, [species_field], source_where) as cursor:
        for (sp,) in cursor:
            species.add(sp)
    if len(species) > 1:
        raise ValueError(
            "The selected groups and the target group are not all the same "
            f"species ({', '.join(str(s) for s in species)}). Nothing was changed."
        )

    # -------------------------
    # Relabel every point in the source groups to the target ID
    # -------------------------
    arcpy.AddMessage(
        f"Merging {len(source_ids)} group(s) into group {target_id}..."
    )
    changed = 0
    with arcpy.da.UpdateCursor(data, [group_field], source_where) as cursor:
        for _ in cursor:
            cursor.updateRow([target_id])
            changed += 1

    arcpy.AddMessage(
        f"Done. {changed} points moved from group(s) {id_list} to group {target_id}."
    )
    arcpy.AddMessage(
        "Re-run step 5 (Choose Representative Point) and step 6 to refresh "
        "the representative points and clusters."
    )