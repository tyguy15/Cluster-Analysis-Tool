import arcpy
import os
from collections import defaultdict

def execute(parameters, messages):
    points_fc      = parameters[0].valueAsText
    species_field  = parameters[1].valueAsText
    buff_field     = parameters[2].valueAsText
    cluster_field  = parameters[3].valueAsText
    workspace_gdb  = parameters[4].valueAsText
    max_search_dist = parameters[5].value  # numeric, meters
    freq_field     = parameters[6].valueAsText

    arcpy.env.overwriteOutput = True
    near_table = os.path.join(workspace_gdb, "near_tbl")

    # -----------------------------
    # PREP — add cluster field if missing
    # -----------------------------
    arcpy.AddMessage("Preparing fields...")
    oid_field = arcpy.Describe(points_fc).OIDFieldName
    existing_fields = [f.name for f in arcpy.ListFields(points_fc)]
    if cluster_field not in existing_fields:
        arcpy.management.AddField(points_fc, cluster_field, "LONG")
        arcpy.AddMessage(f"Added field '{cluster_field}'.")
    if freq_field not in existing_fields:
        arcpy.management.AddField(points_fc, freq_field, "LONG")
        arcpy.AddMessage(f"Added field '{freq_field}'.")

    # -----------------------------
    # BUILD LOOKUP DICTS
    # -----------------------------
    arcpy.AddMessage("Reading species and buffer values...")
    buff_lookup    = {}
    species_lookup = {}
    with arcpy.da.SearchCursor(
        points_fc, [oid_field, species_field, buff_field]
    ) as cursor:
        for oid, sp, buff in cursor:
            buff_lookup[oid]    = buff if buff is not None else 0
            species_lookup[oid] = sp
   
    # -----------------------------
    # CHECK SEARCH DISTANCE CAP
    # Two buffers can overlap at up to the sum of their radii,
    # so the cap should be at least the two largest buffers combined.
    # -----------------------------
    largest = sorted(buff_lookup.values(), reverse=True)[:2]
    needed  = sum(largest)
    if needed > max_search_dist:
        arcpy.AddWarning(
            f"Max search distance ({max_search_dist} m) is smaller than the two "
            f"largest buffers combined ({needed} m). Some overlapping buffers may "
            f"not be clustered. Increase the max search distance to avoid this."
        )      

    # -----------------------------
    # GENERATE NEAR TABLE
    # -----------------------------
    arcpy.AddMessage(f"Generating near table with {max_search_dist}m search radius...")
    if arcpy.Exists(near_table):
        arcpy.management.Delete(near_table)
    arcpy.analysis.GenerateNearTable(
        in_features=points_fc,
        near_features=points_fc,
        out_table=near_table,
        search_radius=f"{max_search_dist} Meters",
        location="NO_LOCATION",
        angle="NO_ANGLE",
        closest="ALL",
        method="PLANAR"
    )

    # -----------------------------
    # UNION-FIND (DISJOINT SET)
    # -----------------------------
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[py] = px

    # -----------------------------
    # PROCESS NEAR PAIRS
    # -----------------------------
    arcpy.AddMessage("Processing near pairs and applying clustering rules...")
    with arcpy.da.SearchCursor(
        near_table, ["IN_FID", "NEAR_FID", "NEAR_DIST"]
    ) as cursor:
        for oid1, oid2, dist in cursor:
            if oid1 == oid2:
                continue
            # Same species only
            if species_lookup.get(oid1) != species_lookup.get(oid2):
                continue
            buff1 = buff_lookup.get(oid1, 0)
            buff2 = buff_lookup.get(oid2, 0)
            # Rule C: containment — point inside buffer
            if dist == 0:
                union(oid1, oid2)
                continue
            # Overlap rule: buffers overlap when the distance between the
            # points is less than the two buffer radii combined
            if dist < buff1 + buff2:
                union(oid1, oid2)

    # -----------------------------
    # ASSIGN CLUSTER IDS
    # -----------------------------
    arcpy.AddMessage("Assigning cluster IDs and cluster frequency...")

    # Count how many points ended up in each cluster
    cluster_sizes = defaultdict(int)
    for oid in species_lookup:
        cluster_sizes[find(oid)] += 1

    cluster_map     = {}
    cluster_counter = 1
    with arcpy.da.UpdateCursor(
        points_fc, [oid_field, cluster_field, freq_field]
    ) as cursor:
        for oid, _, _ in cursor:
            root = find(oid)
            if root not in cluster_map:
                cluster_map[root] = cluster_counter
                cluster_counter += 1
            cursor.updateRow((oid, cluster_map[root], cluster_sizes[root]))

    multi = sum(1 for n in cluster_sizes.values() if n > 1)
    arcpy.AddMessage(
        f"Clustering complete. {cluster_counter - 1} clusters created; "
        f"{multi} contain more than one point."
    )