import arcpy
import os
from collections import defaultdict, deque

def execute(parameters, messages):
    near_table     = parameters[0].valueAsText
    seed_points    = parameters[1].valueAsText
    seed_id_field  = parameters[2].valueAsText
    species_field  = parameters[3].valueAsText
    out_gdb        = parameters[4].valueAsText
    out_table_name = parameters[5].valueAsText

    out_table = os.path.join(out_gdb, out_table_name)
    arcpy.env.overwriteOutput = True

    # ----------------------------------
    # READ NEAR TABLE → GRAPH
    # ----------------------------------
    arcpy.AddMessage("Building graph from near table...")
    graph = defaultdict(set)

    with arcpy.da.SearchCursor(
        near_table,
        ["SeedID_IN", "SeedID_NEAR", "Species_IN"]
    ) as cursor:
        for seed_a, seed_b, species in cursor:
            graph[(species, seed_a)].add(seed_b)
            graph[(species, seed_b)].add(seed_a)

    arcpy.AddMessage(f"Graph built with {len(graph)} nodes from near table.")

    # ----------------------------------
    # ENSURE ISOLATED SEEDS ARE INCLUDED
    # With raw points, deduplicate by SeedID first so we
    # only add each unique seed once rather than once per
    # raw observation row.
    # ----------------------------------
    arcpy.AddMessage("Adding isolated points...")
    seed_species = {}

    with arcpy.da.SearchCursor(
        seed_points,
        [seed_id_field, species_field]
    ) as cursor:
        for seed_id, species in cursor:
            if seed_id not in seed_species:
                seed_species[seed_id] = species
                graph.setdefault((species, seed_id), set())

    isolated = sum(1 for v in graph.values() if len(v) == 0)
    arcpy.AddMessage(
        f"{len(seed_species)} unique FEAT_SEQ IDs found. "
        f"{isolated} are isolated (no neighbors within search distance)."
    )

    # ----------------------------------
    # CONNECTED COMPONENTS (BFS)
    # ----------------------------------
    arcpy.AddMessage("Running graph analysis / connected components...")
    visited = set()
    groups  = []
    group_id = 1

    for (species, seed_id) in graph:
        if (species, seed_id) in visited:
            continue
        queue     = deque([(species, seed_id)])
        component = []
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in graph[node]:
                queue.append((species, neighbor))
        for (_, sid) in component:
            groups.append((sid, species, group_id))
        group_id += 1

    arcpy.AddMessage(
        f"{group_id - 1} occurrence groups created from "
        f"{len(groups)} unique FEAT_SEQ IDs."
    )

    # ----------------------------------
    # WRITE OUTPUT TABLE
    # ----------------------------------
    arcpy.AddMessage("Writing output table...")
    if arcpy.Exists(out_table):
        arcpy.management.Delete(out_table)

    arcpy.management.CreateTable(out_gdb, out_table_name)
    arcpy.management.AddField(out_table, "SeedID",            "LONG")
    arcpy.management.AddField(out_table, "SpeciesID",         "TEXT", field_length=100)
    arcpy.management.AddField(out_table, "OccurrenceGroupID", "LONG")

    with arcpy.da.InsertCursor(
        out_table,
        ["SeedID", "SpeciesID", "OccurrenceGroupID"]
    ) as cursor:
        for row in groups:
            cursor.insertRow(row)

    arcpy.AddMessage(f"Created {group_id - 1} occurrence groups.")
    arcpy.AddMessage(f"Output table: {out_table}")

 # ----------------------------------
    # JOIN OccurrenceGroupID BACK TO MAIN DATASET
    # Same as running Join Field manually:
    #   Input Table    = main dataset (seed_points)
    #   Input Field    = FEAT_SEQ field (seed_id_field)
    #   Join Table     = the output table just created
    #   Join Field     = SeedID
    #   Transfer Field = OccurrenceGroupID
    # ----------------------------------
    arcpy.AddMessage("Joining OccurrenceGroupID back to the main dataset...")

    # If this tool was run before, the field is already there.
    # Remove it so the join doesn't create OccurrenceGroupID_1.
    existing_fields = [f.name for f in arcpy.ListFields(seed_points)]
    if "OccurrenceGroupID" in existing_fields:
        arcpy.AddMessage("OccurrenceGroupID already exists in the main dataset; replacing it.")
        arcpy.management.DeleteField(seed_points, "OccurrenceGroupID")

    arcpy.management.JoinField(
        in_data=seed_points,
        in_field=seed_id_field,
        join_table=out_table,
        join_field="SeedID",
        fields=["OccurrenceGroupID"]
    )
    arcpy.AddMessage("OccurrenceGroupID added to the main dataset.")