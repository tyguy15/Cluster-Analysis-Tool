import arcpy
from collections import defaultdict
from datetime import datetime

# ---------- Helper functions ---------- #
def normalize_date(value):
    """Convert date to a consistent YYYY-MM-DD string regardless of input type."""
    if value is None:
        return None
    # Already a datetime object
    if hasattr(value, 'date'):
        return value.date().isoformat()
    # Stored as a string — try common formats
    value = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y"
    ):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    # Fallback — strip time component by splitting on space or T
    return value.split(" ")[0].split("T")[0]

def normalize_observer(value):
    """Normalize observer to a consistent lowercase stripped string."""
    if value is None:
        return None
    return str(value).strip().lower()

# -------------------------------------------- #

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
    else:
        arcpy.AddMessage(f"Field '{concat_field}' already exists.")

    # ---------- Group rows by OccurrenceID + Observer + Date ---------- #
    arcpy.AddMessage("Grouping rows by occurrence, observer, and date...")
    groups = defaultdict(list)
    search_fields = ["OID@", occ_field, observer_field, date_field, note_field, rep_field]

    with arcpy.da.SearchCursor(table, search_fields) as cursor:
        for oid, occ, observer, date, note, is_rep in cursor:
            date_key     = normalize_date(date)
            observer_key = normalize_observer(observer)
            key = (occ, observer_key, date_key)
            groups[key].append({
                "oid":    oid,
                "note":   note,
                "is_rep": is_rep
            })

    arcpy.AddMessage(
        f"Found {len(groups)} unique Occurrence + Observer + Date combinations."
    )

    # ---------- Diagnostic sample ---------- #
    arcpy.AddMessage("Sample group keys (first 5):")
    for i, key in enumerate(list(groups.keys())[:5]):
        occ, obs, dt = key
        count = len(groups[key])
        arcpy.AddMessage(
            f"  OccurrenceID={occ} | Observer={obs} | Date={dt} | Rows={count}"
        )

    # ---------- Determine keepers + concatenate notes ---------- #
    arcpy.AddMessage("Identifying keeper records and concatenating notes...")
    notes_by_oid   = {}
    oids_to_delete = set()
    no_rep_groups  = []

    for key, records in groups.items():
        # Prefer representative-flagged record, fall back to first record
        rep_records = [r for r in records if r["is_rep"] == 1]
        if rep_records:
            keeper = rep_records[0]
        else:
            keeper = records[0]
            no_rep_groups.append(key)

        keeper_oid = keeper["oid"]

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
