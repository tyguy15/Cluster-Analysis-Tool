import arcpy

def execute(parameters, messages):
    input_fc = parameters[0].valueAsText
    field_name = parameters[1].valueAsText

    # Check if field already exists, if not add it
    existing_fields = [f.name for f in arcpy.ListFields(input_fc)]
    if field_name not in existing_fields:
        arcpy.management.AddField(input_fc, field_name, "LONG")
        arcpy.AddMessage(f"Added field '{field_name}' to {input_fc}")
    else:
        arcpy.AddMessage(f"Field '{field_name}' already exists, populating it.")

    # Populate the field with sequential integers
    with arcpy.da.UpdateCursor(input_fc, [field_name]) as cursor:
        i = 1
        for row in cursor:
            row[0] = i
            cursor.updateRow(row)
            i += 1

    arcpy.AddMessage(f"Successfully populated '{field_name}' with sequential IDs (1 to {i - 1}).")