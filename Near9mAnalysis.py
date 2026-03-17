import arcpy
import os

def execute(parameters, messages):
    in_points       = parameters[0].valueAsText
    seed_id_field   = parameters[1].valueAsText
    species_field   = parameters[2].valueAsText
    search_distance = parameters[3].valueAsText
    out_gdb         = parameters[4].valueAsText
    out_table_name  = parameters[5].valueAsText

    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = out_gdb
    out_near_table = os.path.join(out_gdb, out_table_name)

    # -------------------------------------------------
    # BUILD SEED ID + SPECIES LOOKUP FROM RAW POINTS
    # Since points are no longer dissolved, multiple rows
    # may share a SeedID. We just need one species value
    # per SeedID (they should all be the same species).
    # -------------------------------------------------
    arcpy.AddMessage("Building SeedID lookups from raw points...")
    oid_to_seed    = {}
    oid_to_species = {}
    seed_to_species = {}

    with arcpy.da.SearchCursor(
        in_points, ["OID@", seed_id_field, species_field]
    ) as cursor:
        for oid, seed_id, species in cursor:
            oid_to_seed[oid]    = seed_id
            oid_to_species[oid] = species
            seed_to_species[seed_id] = species

    arcpy.AddMessage(
        f"Found {len(oid_to_seed)} raw points across "
        f"{len(seed_to_species)} unique SeedIDs."
    )

    # -------------------------------------------------
    # GENERATE NEAR TABLE (SELF)
    # -------------------------------------------------
    arcpy.AddMessage("Generating near table...")
    arcpy.analysis.GenerateNearTable(
        in_features=in_points,
        near_features=in_points,
        out_table=out_near_table,
        search_radius=search_distance,
        location="NO_LOCATION",
        angle="NO_ANGLE",
        closest="ALL",
        closest_count=0
    )

    # -------------------------------------------------
    # JOIN SEED ID + SPECIES FOR BOTH SIDES
    # Join on OBJECTID as before, then we use the
    # seed/species values to filter — not OBJECTID itself
    # -------------------------------------------------
    arcpy.AddMessage("Joining SeedID and Species for IN_FID...")
    arcpy.management.JoinField(
        in_data=out_near_table,
        in_field="IN_FID",
        join_table=in_points,
        join_field="OBJECTID",
        fields=[seed_id_field, species_field]
    )
    arcpy.management.AlterField(
        out_near_table, seed_id_field,
        new_field_name="SeedID_IN", new_field_alias="SeedID_IN"
    )
    arcpy.management.AlterField(
        out_near_table, species_field,
        new_field_name="Species_IN", new_field_alias="Species_IN"
    )

    arcpy.AddMessage("Joining SeedID and Species for NEAR_FID...")
    arcpy.management.JoinField(
        in_data=out_near_table,
        in_field="NEAR_FID",
        join_table=in_points,
        join_field="OBJECTID",
        fields=[seed_id_field, species_field]
    )
    arcpy.management.AlterField(
        out_near_table, seed_id_field,
        new_field_name="SeedID_NEAR", new_field_alias="SeedID_NEAR"
    )
    arcpy.management.AlterField(
        out_near_table, species_field,
        new_field_name="Species_NEAR", new_field_alias="Species_NEAR"
    )

    # -------------------------------------------------
    # REMOVE SELF-MATCHES AND SAME-SEED PAIRS
    # With raw points, IN_FID != NEAR_FID is not enough —
    # two different OBJECTIDs can share the same SeedID
    # (same visit, multiple raw points). We remove those
    # too since they aren't meaningful pairs.
    # -------------------------------------------------
    arcpy.AddMessage("Removing self-matches and same-SeedID pairs...")
    removed = 0
    with arcpy.da.UpdateCursor(
        out_near_table, ["IN_FID", "NEAR_FID", "SeedID_IN", "SeedID_NEAR"]
    ) as cursor:
        for in_fid, near_fid, seed_in, seed_near in cursor:
            if in_fid == near_fid or seed_in == seed_near:
                cursor.deleteRow()
                removed += 1
    arcpy.AddMessage(f"Removed {removed} self-match / same-SeedID rows.")

    # -------------------------------------------------
    # FILTER TO SAME-SPECIES PAIRS ONLY
    # -------------------------------------------------
    arcpy.AddMessage("Filtering to same-species pairs...")
    same_species_view = "same_species_near_view"
    arcpy.management.MakeTableView(
        out_near_table,
        same_species_view,
        "Species_IN = Species_NEAR"
    )
    filtered_table = os.path.join(out_gdb, f"{out_table_name}_SameSpecies")
    arcpy.management.CopyRows(same_species_view, filtered_table)

    # -------------------------------------------------
    # DEDUPLICATE SEED PAIRS
    # With multiple raw points per SeedID, the same
    # SeedID pair (A→B) can appear many times in the
    # near table. Collapse to one row per unique pair
    # so Tool 3 graph analysis isn't artificially inflated.
    # -------------------------------------------------
    arcpy.AddMessage("Deduplicating SeedID pairs...")
    seen_pairs = set()
    duplicate_oids = []

    with arcpy.da.SearchCursor(
        filtered_table, ["OID@", "SeedID_IN", "SeedID_NEAR"]
    ) as cursor:
        for oid, seed_in, seed_near in cursor:
            pair = (min(seed_in, seed_near), max(seed_in, seed_near))
            if pair in seen_pairs:
                duplicate_oids.append(oid)
            else:
                seen_pairs.add(pair)

    if duplicate_oids:
        with arcpy.da.UpdateCursor(
            filtered_table, ["OID@"]
        ) as cursor:
            for (oid,) in cursor:
                if oid in duplicate_oids:
                    cursor.deleteRow()

    arcpy.AddMessage(
        f"Removed {len(duplicate_oids)} duplicate SeedID pairs. "
        f"{len(seen_pairs)} unique same-species pairs remain."
    )
    arcpy.AddMessage(f"Near table complete:            {out_near_table}")
    arcpy.AddMessage(f"Same-species filtered table:    {filtered_table}")

    arcpy.AddMessage(f"Near table complete: {out_near_table}")
    arcpy.AddMessage(f"Same-species filtered table: {filtered_table}")
