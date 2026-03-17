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
    seed_species = {}

    with arcpy.da.SearchCursor(
        near_table,
        ["SeedID_IN", "SeedID_NEAR", "Species_IN"]
    ) as cursor:
        for seed_a, seed_b, species in cursor:
            graph[(species, seed_a)].add(seed_b)
            graph[(species, seed_b)].add(seed_a)

    # ----------------------------------
    # ENSURE ISOLATED SEEDS ARE INCLUDED
    # ----------------------------------
    arcpy.AddMessage("Adding isolated seeds...")
    with arcpy.da.SearchCursor(
        seed_points,
        [seed_id_field, species_field]
    ) as cursor:
        for seed_id, species in cursor:
            seed_species[seed_id] = species
            graph.setdefault((species, seed_id), set())

    # ----------------------------------
    # CONNECTED COMPONENTS (BFS)
    # ----------------------------------
    arcpy.AddMessage("Running graph analysis / connected components...")
    visited = set()
    groups = []
    group_id = 1

    for (species, seed_id) in graph:
        if (species, seed_id) in visited:
            continue
        queue = deque([(species, seed_id)])
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

    # ----------------------------------
    # WRITE OUTPUT TABLE
    # ----------------------------------
    arcpy.AddMessage("Writing output table...")

    # Drop and recreate if it already exists
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