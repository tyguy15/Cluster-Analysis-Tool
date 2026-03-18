import arcpy
from collections import defaultdict

def execute(parameters, messages):
    table          = parameters[0].valueAsText
    occ_field      = parameters[1].valueAsText
    observer_field = parameters[2].valueAsText
    date_field     = parameters[3].valueAsText
    note_field     = parameters[4].valueAsText
    rep_field      = parameters[5].valueAsText
    concat_field   = parameters[6].valueAsText
    delimiter      = parameters[7].valueAsText
    concat_length  = parameters[8].value

    arcpy.env.overwriteOutput = True

    # ---------- Ensure concat field exists ---------- #
    arcpy.AddMessage("Checking fields...")
    existing_fields = [f.name for f in arcpy.ListFields(table)]
    if concat_field not in existing_fields:
        arcpy.management.AddField(
            table, concat_field, "TEXT",
            field_length=concat_length
        )
        arcpy.AddMessage(f"Added field: '{concat_field}'.")

    # ---------- Group rows by OccurrenceID + Observer + Date ---------- #
    # This is the key change — we group by who visited and when,
    # not by SeedID, so all GPS points from the same person on
    # the same day at the same occurrence collapse into one visit.
    arcpy.AddMessage("Grouping rows by occurrence, observer, and date...")
    groups = defaultdict(list)
    search_fields = ["OID@", occ_field, observer_field, date_field, note_field, rep_field]

    with arcpy.da.SearchCursor(table, search_fields) as cursor:
        for oid, occ, observer, date, note, is_rep in cursor:
            # Normalize date to date-only (strip time component if present)
            # so that two records from the same day but different timestamps
            # are treated as the same visit
            date_key = date.date() if date is not None else None
            key = (occ, observer, date_key)
            groups[key].append({
                "oid":    oid,
                "note":   note,
                "is_rep": is_rep
            })

    arcpy.AddMessage(
        f"Found {len(groups)} unique Occurrence + Observer + Date combinations."
    )

    # ---------- Determine keepers + concatenate notes ---------- #
    # Keeper priority: representative-flagged row first, then first record
    arcpy.AddMessage("Identifying keeper records and concatenating notes...")
    notes_by_oid   = {}
    oids_to_delete = set()

    for key, records in groups.items():
        # Prefer the representative-flagged record
        rep_records = [r for r in records if r["is_rep"] == 1]
        keeper      = rep_records[0] if rep_records else records[0]
        keeper_oid  = keeper["oid"]

        # Collect unique non-empty notes from ALL records in group
        seen  = set()
        notes = []
        for r in records:
            note = r["note"]
            if note:
                note = str(note).strip()
                if note and note not in seen:
                    seen.add(note)
                    notes.append(note)

        concat_text = delimiter.join(notes)
        if len(concat_text) > concat_length:
            concat_text = concat_text[:concat_length]
        notes_by_oid[keeper_oid] = concat_text

        # Mark non-keeper, non-representative rows for deletion
        for r in records:
            if r["oid"] != keeper_oid and r["is_rep"] != 1:
                oids_to_delete.add(r["oid"])

    arcpy.AddMessage(f"Keeper rows:              {len(notes_by_oid)}")
    arcpy.AddMessage(f"Rows marked for deletion: {len(oids_to_delete)}")

    # ---------- Sanity check ---------- #
    # Warn if any group had no representative flagged — means
    # Tool 4 may not have been run yet or rep field is not populated
    no_rep_groups = [
        k for k, records in groups.items()
        if not any(r["is_rep"] == 1 for r in records)
    ]
    if no_rep_groups:
        arcpy.AddWarning(
            f"{len(no_rep_groups)} visit groups had no representative-flagged "
            f"record. First record was used as fallback. Consider running "
            f"ChooseRepresentativePoint before this tool."
        )

    # ---------- Update keepers + delete duplicates ---------- #
    arcpy.AddMessage("Updating keeper rows and removing duplicates...")
    updated_count = 0
    deleted_count = 0

    with arcpy.da.UpdateCursor(
        table, ["OID@", concat_field, rep_field]
    ) as cursor:
        for oid, concat_val, is_rep in cursor:
            if oid in notes_by_oid:
                cursor.updateRow((oid, notes_by_oid[oid], is_rep))
                updated_count += 1
            elif oid in oids_to_delete:
                cursor.deleteRow()
                deleted_count += 1

    arcpy.AddMessage("---------- COMPLETE ----------")
    arcpy.AddMessage(f"Updated rows:                      {updated_count}")
    arcpy.AddMessage(f"Deleted duplicates (non-rep only): {deleted_count}")