import arcpy

def execute(parameters, messages):
    fc            = parameters[0].valueAsText
    occurrence_id = parameters[1].valueAsText
    buff_field    = parameters[2].valueAsText
    date_field    = parameters[3].valueAsText
    rep_field     = parameters[4].valueAsText

    arcpy.env.overwriteOutput = True

    # -------------------------
    # Step 1: Add / reset rep field
    # -------------------------
    arcpy.AddMessage(f"Resetting '{rep_field}' field...")
    existing_fields = [f.name for f in arcpy.ListFields(fc)]
    if rep_field not in existing_fields:
        arcpy.management.AddField(fc, rep_field, "SHORT")
        arcpy.AddMessage(f"Added field '{rep_field}'.")
    arcpy.management.CalculateField(fc, rep_field, 0)

    # -------------------------
    # Step 2: Read OBJECTIDs in sorted priority order
    #         Priority: smallest buffer first, then most recent date
    # -------------------------
    arcpy.AddMessage("Identifying representative records...")
    order_by = f"ORDER BY {occurrence_id} ASC, {buff_field} ASC, {date_field} DESC"
    seen     = set()
    rep_oids = set()

    with arcpy.da.SearchCursor(
        fc,
        ["OBJECTID", occurrence_id],
        sql_clause=(None, order_by)
    ) as cursor:
        for oid, occ in cursor:
            if occ not in seen:
                rep_oids.add(oid)
                seen.add(occ)

    # -------------------------
    # Step 3: Flag representatives in original FC
    # -------------------------
    arcpy.AddMessage(f"Flagging {len(rep_oids)} representative records...")
    with arcpy.da.UpdateCursor(fc, ["OBJECTID", rep_field]) as cursor:
        for oid, rep in cursor:
            if oid in rep_oids:
                cursor.updateRow([oid, 1])

    arcpy.AddMessage(
        f"Done. {len(rep_oids)} representative points assigned "
        f"(one per {occurrence_id})."
    )