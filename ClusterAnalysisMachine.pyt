import arcpy

# ----------------------------------------------------------------
# TOOLBOX DEFINITION
# ----------------------------------------------------------------
class Toolbox:
    def __init__(self):
        self.label   = "Cluster Analysis Toolbox"
        self.alias   = "ClusterAnalysisTools"
        self.tools   = [
            AddAnotherID,
            Near9mAnalysis,
            GraphAnalysisAssignOccurrenceID,
            OccurrenceGroupSummary,
            ChooseRepresentativePoint,
            PolygonClusterAnalysis,
            ConsolidateVisits
        ]

# ----------------------------------------------------------------
# TOOL 1 — Add Sequential ID
# ----------------------------------------------------------------
class AddAnotherID:
    def __init__(self):
        self.label       = "1. Add Sequential ID"
        self.description = "Adds a stable sequential integer ID field to a feature class."

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Input Feature Class",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param1 = arcpy.Parameter(
            displayName="ID Field Name",
            name="field_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param1.value = "AnotherID"
        return [param0, param1]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import AddAnotherID as t
        t.execute(parameters, messages)

# ----------------------------------------------------------------
# TOOL 2 — Generate Near Table
# ----------------------------------------------------------------
class Near9mAnalysis:
    def __init__(self):
        self.label       = "2. Near 9m Analysis"
        self.description = "Generates same-species pairs within a search distance."

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Input Points Layer",
            name="in_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param1 = arcpy.Parameter(
            displayName="Seed / Visit ID Field",
            name="seed_id_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param1.parameterDependencies = [param0.name]

        param2 = arcpy.Parameter(
            displayName="Species ID Field",
            name="species_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param2.parameterDependencies = [param0.name]

        param3 = arcpy.Parameter(
            displayName="Search Distance",
            name="search_distance",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input"
        )
        param3.value = "9 Meters"

        param4 = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="out_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param5 = arcpy.Parameter(
            displayName="Output Table Name",
            name="out_table_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param5.value = "Seeds_Near_9m"
        return [param0, param1, param2, param3, param4, param5]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import Near9mAnalysis as t
        t.execute(parameters, messages)

# ----------------------------------------------------------------
# TOOL 3 — Graph Analysis
# ----------------------------------------------------------------
class GraphAnalysisAssignOccurrenceID:
    def __init__(self):
        self.label       = "3. Graph Analysis — Assign Occurrence ID"
        self.description = "Assigns OccurrenceGroupIDs using connected components graph analysis."

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Near Table (Same Species)",
            name="near_table",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input"
        )
        param1 = arcpy.Parameter(
            displayName="Seed Points Layer",
            name="seed_points",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param2 = arcpy.Parameter(
            displayName="Seed / Visit ID Field",
            name="seed_id_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param2.parameterDependencies = [param1.name]

        param3 = arcpy.Parameter(
            displayName="Species ID Field",
            name="species_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param3.parameterDependencies = [param1.name]

        param4 = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="out_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param5 = arcpy.Parameter(
            displayName="Output Table Name",
            name="out_table_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param5.value = "Seed_OccurrenceGroups"
        return [param0, param1, param2, param3, param4, param5]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import GraphAnalysis_AssignOccurrenceID as t
        t.execute(parameters, messages)

# ----------------------------------------------------------------
# TOOL 4 — Occurrence Group Summary
# ----------------------------------------------------------------
class OccurrenceGroupSummary:
    def __init__(self):
        self.label       = "4. Occurrence Group Summary"
        self.description = (
            "Calculates point count and bounding diameter per occurrence "
            "group and flags groups exceeding a user-defined extent threshold."
        )

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Input Feature Class",
            name="fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param1 = arcpy.Parameter(
            displayName="Occurrence Group ID Field",
            name="occ_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param1.parameterDependencies = [param0.name]
        param1.filter.list = ["Short", "Long"]

        param2 = arcpy.Parameter(
            displayName="Seed ID Field",
            name="seed_id_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param2.parameterDependencies = [param0.name]

        param3 = arcpy.Parameter(
            displayName="Large Extent Flag Threshold (meters)",
            name="extent_threshold",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        param4 = arcpy.Parameter(
            displayName="Point Count Field Name",
            name="point_count_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param4.value = "occ_point_count"

        param5 = arcpy.Parameter(
            displayName="Bounding Diameter Field Name",
            name="diameter_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param5.value = "occ_diameter_m"

        param6 = arcpy.Parameter(
            displayName="Large Extent Flag Field Name",
            name="flag_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param6.value = "flag_large_extent"

        return [param0, param1, param2, param3, param4, param5, param6]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import OccurrenceGroupSummary as t
        t.execute(parameters, messages)

# ----------------------------------------------------------------
# TOOL 5 — Choose Representative Point
# ----------------------------------------------------------------
class ChooseRepresentativePoint:
    def __init__(self):
        self.label       = "5. Choose Representative Point"
        self.description = "Flags one representative record per occurrence group."

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Input Feature Class",
            name="input_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param1 = arcpy.Parameter(
            displayName="Occurrence Group ID Field",
            name="occurrence_id",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param1.parameterDependencies = [param0.name]
        param1.filter.list = ["Short", "Long"]

        param2 = arcpy.Parameter(
            displayName="Buffer Distance Field",
            name="buff_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param2.parameterDependencies = [param0.name]
        param2.filter.list = ["Short", "Long", "Double", "Single"]

        param3 = arcpy.Parameter(
            displayName="Observation Date Field",
            name="date_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param3.parameterDependencies = [param0.name]
        param3.filter.list = ["Date"]

        param4 = arcpy.Parameter(
            displayName="Is Representative Field Name",
            name="rep_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param4.value = "is_representative"
        return [param0, param1, param2, param3, param4]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import ChooseRepresentativePoint as t
        t.execute(parameters, messages)

# ----------------------------------------------------------------
# TOOL 6 — Polygon Cluster Analysis
# ----------------------------------------------------------------
class PolygonClusterAnalysis:
    def __init__(self):
        self.label       = "6. Polygon Cluster Analysis"
        self.description = "Clusters points by species and buffer distance using Union-Find."

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Input Points Feature Class",
            name="points_fc",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        param1 = arcpy.Parameter(
            displayName="Species ID Field",
            name="species_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param1.parameterDependencies = [param0.name]
        param1.filter.list = []

        param2 = arcpy.Parameter(
            displayName="Buffer Distance Field",
            name="buff_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param2.parameterDependencies = [param0.name]
        param2.filter.list = ["Short", "Long", "Double", "Single"]

        param3 = arcpy.Parameter(
            displayName="Cluster ID Field Name",
            name="cluster_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param3.value = "cluster_id"

        param4 = arcpy.Parameter(
            displayName="Temp Workspace Geodatabase",
            name="workspace_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )
        param5 = arcpy.Parameter(
            displayName="Max Search Distance (meters)",
            name="max_search_dist",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        param5.value = 500
        return [param0, param1, param2, param3, param4, param5]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import PolygonClusterAnalysis as t
        t.execute(parameters, messages)

# ----------------------------------------------------------------
# TOOL 7 — Consolidate Visits
# ----------------------------------------------------------------
class ConsolidateVisits:
    def __init__(self):
        self.label       = "7. Consolidate Visits"
        self.description = "Deduplicates visits per occurrence and concatenates notes."
    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Input Table / Feature Class",
            name="table",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input"
        )
        param1 = arcpy.Parameter(
            displayName="Occurrence Group ID Field",
            name="occ_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param1.parameterDependencies = [param0.name]
        param1.filter.list = ["Short", "Long"]

        param2 = arcpy.Parameter(
            displayName="Observer Field",
            name="observer_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param2.parameterDependencies = [param0.name]

        param3 = arcpy.Parameter(
            displayName="Observation Date Field",
            name="date_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param3.parameterDependencies = [param0.name]
        param3.filter.list = ["Date"]

        param4 = arcpy.Parameter(
            displayName="Note Field",
            name="note_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param4.parameterDependencies = [param0.name]

        param5 = arcpy.Parameter(
            displayName="Is Representative Field",
            name="rep_field",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )
        param5.parameterDependencies = [param0.name]
        param5.filter.list = ["Short", "Long"]

        param6 = arcpy.Parameter(
            displayName="Concatenated Note Field Name",
            name="concat_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param6.value = "VisitNote_concat"

        param7 = arcpy.Parameter(
            displayName="Note Delimiter",
            name="delimiter",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        param7.value = " | "

        param8 = arcpy.Parameter(
            displayName="Max Concatenated Note Length",
            name="concat_length",
            datatype="GPLong",
            parameterType="Required",
            direction="Input"
        )
        param8.value = 2000
        return [param0, param1, param2, param3, param4, param5, param6, param7, param8]
    

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import ConsolidateVisits as t
        t.execute(parameters, messages)