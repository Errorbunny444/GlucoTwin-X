import adsk.core, adsk.fusion, adsk.cam, traceback
import os

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = app.activeProduct

        if not design:
            ui.messageBox('No active Fusion design. Please open a new design first (File > New Design).', 'GlucoTwin-X Generator')
            return

        rootComp = design.rootComponent
        
        # Determine export directories
        script_dir = os.path.dirname(os.path.realpath(__file__))
        cad_export_dir = os.path.abspath(os.path.join(script_dir, '..', '..', 'exports'))
        unity_export_dir = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..', 'unity', 'Assets', 'Game', 'Models', 'Fusion360'))
        
        for d in [cad_export_dir, unity_export_dir]:
            if not os.path.exists(d):
                try:
                    os.makedirs(d)
                except Exception:
                    pass

        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        extrudes = rootComp.features.extrudeFeatures

        # -------------------------------------------------------------
        # 1. Create Pancreas (Elongated curved organ)
        # -------------------------------------------------------------
        pancreasSketch = sketches.add(xyPlane)
        pancreasSketch.sketchCurves.sketchEllipses.add(
            adsk.core.Point3D.create(5.0, 0.0, 0.0),
            adsk.core.Point3D.create(12.0, 0.0, 0.0),
            adsk.core.Point3D.create(5.0, 2.0, 0.0)
        )
        pancreasProf = pancreasSketch.profiles.item(0)
        pancreasExtInput = extrudes.createInput(pancreasProf, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        pancreasExtInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(2.5))
        pancreasExtrude = extrudes.add(pancreasExtInput)
        pancreasBody = pancreasExtrude.bodies.item(pancreasExtrude.bodies.count - 1)
        pancreasBody.name = "Pancreas"

        # -------------------------------------------------------------
        # 2. Create Stomach (Upper Left reservoir)
        # -------------------------------------------------------------
        stomachSketch = sketches.add(xyPlane)
        stomachSketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(-6.0, 4.0, 0.0), 
            4.5
        )
        stomachProf = stomachSketch.profiles.item(0)
        stomachExtInput = extrudes.createInput(stomachProf, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        stomachExtInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(5.0))
        stomachExtrude = extrudes.add(stomachExtInput)
        stomachBody = stomachExtrude.bodies.item(stomachExtrude.bodies.count - 1)
        stomachBody.name = "Stomach"

        # -------------------------------------------------------------
        # 3. Create Intestine (Lower absorption tract)
        # -------------------------------------------------------------
        intSketch = sketches.add(xyPlane)
        intSketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(-3.0, -6.0, 0.0), 
            5.5
        )
        intProf = intSketch.profiles.item(0)
        intExtInput = extrudes.createInput(intProf, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        intExtInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(4.0))
        intExtrude = extrudes.add(intExtInput)
        intestineBody = intExtrude.bodies.item(intExtrude.bodies.count - 1)
        intestineBody.name = "Intestine"

        # -------------------------------------------------------------
        # 4. Create Bloodstream Loop (Circulatory ring around organs)
        # -------------------------------------------------------------
        bloodSketch = sketches.add(xyPlane)
        bloodSketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0.0, 0.0, 0.0), 12.0)
        bloodSketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0.0, 0.0, 0.0), 10.5)
        
        # Pick the annular ring profile
        bloodProf = None
        for p in bloodSketch.profiles:
            if p.profileLoops.count > 1:
                bloodProf = p
                break
        if not bloodProf:
            bloodProf = bloodSketch.profiles.item(0)

        bloodExtInput = extrudes.createInput(bloodProf, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        bloodExtInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(0.8))
        bloodExtrude = extrudes.add(bloodExtInput)
        bloodBody = bloodExtrude.bodies.item(bloodExtrude.bodies.count - 1)
        bloodBody.name = "BloodstreamPath"

        # -------------------------------------------------------------
        # 5. Export Meshes for Unity and CAD
        # -------------------------------------------------------------
        exportMgr = design.exportManager
        bodies_to_export = [
            (pancreasBody, "pancreas"),
            (stomachBody, "stomach"),
            (intestineBody, "intestine"),
            (bloodBody, "bloodstream_path")
        ]

        export_count = 0
        dest_dirs = [cad_export_dir]
        if os.path.exists(unity_export_dir):
            dest_dirs.append(unity_export_dir)

        for body, name in bodies_to_export:
            for out_dir in dest_dirs:
                # 1. Try OBJ export
                obj_file = os.path.join(out_dir, f"{name}.obj")
                try:
                    objOptions = exportMgr.createOBJExportOptions(body, obj_file)
                    exportMgr.execute(objOptions)
                    export_count += 1
                except Exception:
                    try:
                        objOptions = exportMgr.createOBJExportOptions(obj_file, body)
                        exportMgr.execute(objOptions)
                        export_count += 1
                    except Exception:
                        pass

                # 2. Try STL export (broadly supported by Unity and 3D viewers)
                stl_file = os.path.join(out_dir, f"{name}.stl")
                try:
                    stlOptions = exportMgr.createSTLExportOptions(body, stl_file)
                    exportMgr.execute(stlOptions)
                    export_count += 1
                except Exception:
                    try:
                        stlOptions = exportMgr.createSTLExportOptions(stl_file, body)
                        exportMgr.execute(stlOptions)
                        export_count += 1
                    except Exception:
                        pass

        # 3. Export entire assembly / design as FBX and OBJ
        for out_dir in dest_dirs:
            full_fbx = os.path.join(out_dir, "gluctwin_anatomy.fbx")
            try:
                fbxOptions = exportMgr.createFBXExportOptions(full_fbx, rootComp)
                exportMgr.execute(fbxOptions)
                export_count += 1
            except Exception:
                try:
                    fbxOptions = exportMgr.createFBXExportOptions(full_fbx)
                    exportMgr.execute(fbxOptions)
                    export_count += 1
                except Exception:
                    pass

        # Try to save the active document
        doc = app.activeDocument
        if doc and not doc.isSaved:
            try:
                doc.save('GlucoTwin_Metabolic_Anatomy')
            except Exception:
                pass

        ui.messageBox(
            f"GlucoTwin-X Metabolic CAD Generator Complete!\n\n"
            f"Bodies Created:\n"
            f" - Pancreas (Endocrine)\n"
            f" - Stomach (Digestion)\n"
            f" - Intestine (Absorption)\n"
            f" - BloodstreamPath (Circulation)\n\n"
            f"Exported {export_count} files to:\n"
            f"{cad_export_dir}\n"
            f"and Unity Assets folder.",
            "GlucoTwin-X Generator"
        )

    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()), 'GlucoTwin-X Error')
