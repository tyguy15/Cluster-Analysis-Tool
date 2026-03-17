import arcpy
import os

def execute(parameters, messages):
    in_points       = parameters[0].valueAsText
    seed_id_field   = parameters[1].valueAsText
    species_field   = parameters[2].valueAsText
    search_distance = parameters[3].valueAsText  # e.g. "9 Meters"
    out_gdb         = parameters[4].valueAsText
    out_table_name  = parameters[5].valueAsText

    # -------------------------------------------------
    # ENVIRONMENT
    # -------------------------------------------------
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = out_gdb
    out_near_table = os.path.join(out_gdb, out_table_name)

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
    # REMOVE SELF-MATCHES
    # -------------------------------------------------
    arcpy.AddMessage("Removing self-matches...")
    with arcpy.da.UpdateCursor(out_near_table, ["IN_FID", "NEAR_FID"]) as cursor:
        for row in cursor:
            if row[0] == row[1]:
                cursor.deleteRow()

    # -------------------------------------------------
    # JOIN SPECIES + SEED ID (IN_FID side)
    # -------------------------------------------------
    arcpy.AddMessage("Joining fields for IN_FID...")
    arcpy.management.JoinField(
        in_data=out_near_table,
        in_field="IN_FID",
        join_table=in_points,
        join_field="OBJECTID",
        fields=[species_field, seed_id_field]
    )
    arcpy.management.AlterField(
        out_near_table, species_field,
        new_field_name="Species_IN", new_field_alias="Species_IN"
    )
    arcpy.management.AlterField(
        out_near_table, seed_id_field,
        new_field_name="SeedID_IN", new_field_alias="SeedID_IN"
    )

    # -------------------------------------------------
    # JOIN SPECIES + SEED ID (NEAR_FID side)
    # -------------------------------------------------
    arcpy.AddMessage("Joining fields for NEAR_FID...")
    arcpy.management.JoinField(
        in_data=out_near_table,
        in_field="NEAR_FID",
        join_table=in_points,
        join_field="OBJECTID",
        fields=[species_field, seed_id_field]
    )
    arcpy.management.AlterField(
        out_near_table, species_field,
        new_field_name="Species_NEAR", new_field_alias="Species_NEAR"
    )
    arcpy.management.AlterField(
        out_near_table, seed_id_field,
        new_field_name="SeedID_NEAR", new_field_alias="SeedID_NEAR"
    )

    # -------------------------------------------------
    # FILTER TO SAME-SPECIES PAIRS
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

    arcpy.AddMessage(f"Near table complete: {out_near_table}")
    arcpy.AddMessage(f"Same-species filtered table: {filtered_table}")