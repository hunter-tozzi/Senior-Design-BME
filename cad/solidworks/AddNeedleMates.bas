Attribute VB_Name = "AddNeedleMates"
' =============================================================================
' Self-tapping bone marrow needle - add motion mates (SOLIDWORKS VBA macro)
'
' 1. File > Open > cad/step/00_full_assembly.step (Assembly template, mm).
' 2. Tools > Macro > New... save e.g. AddNeedleMates.swp, then in the VBA editor
'    File > Import File... > this .bas file (or paste it), and run "main".
' 3. File > Save As > .SLDASM.
'
' The parts are already in their assembled positions, so the mates do not move
' anything; they only add the degrees of freedom of the mechanism:
'   - push cap / drive nut slides 30 mm, cannot rotate (limit distance)
'   - nut drives the spiral shaft through a SCREW mate (50 mm/rev, left-hand)
'   - shaft drives the cannula hub through a GEAR mate (1:1, push stroke)
'   - pawl rides on its post, stylet keyed in the hub, top port in the cap
' Housing, bottom plug, top cover ring and sliding base stay Fixed.
'
' Faces are found by geometry (cylinder radius + axis, or plane height), so
' the macro does not depend on face IDs. Units in the API are metres.
' =============================================================================

Dim swApp As Object
Dim swModel As Object
Dim swAssy As Object
Dim swSelMgr As Object
Dim report As String
Dim nOK As Integer, nFail As Integer

Const MM As Double = 0.001
Const TOL As Double = 0.00001          ' 10 um match tolerance

Sub main()
    Set swApp = Application.SldWorks
    If IsEmpty(swDocASSEMBLY) Then
        MsgBox "In the VBA editor enable Tools > References > 'SOLIDWORKS <version> Constant type library', then run again.", vbExclamation
        Exit Sub
    End If
    Set swModel = swApp.ActiveDoc
    If swModel Is Nothing Then
        MsgBox "Open cad/step/00_full_assembly.step first.", vbExclamation: Exit Sub
    End If
    If swModel.GetType <> swDocASSEMBLY Then
        MsgBox "The active document must be the needle assembly.", vbExclamation: Exit Sub
    End If
    Set swAssy = swModel
    Set swSelMgr = swModel.SelectionManager
    swAssy.ResolveAllLightWeightComponents False

    Dim housing As Object, plug As Object, hub As Object, shaft As Object, pawl As Object
    Dim nut As Object, cover As Object, port As Object, stylet As Object, baseComp As Object
    Set housing = GetComp("01_housing")
    Set plug = GetComp("02_bottom_plug")
    Set hub = GetComp("03_cannula_hub")
    Set shaft = GetComp("04_spiral_shaft_carrier")
    Set pawl = GetComp("05_rocker_pawl")
    Set nut = GetComp("06_push_cap_drive_nut")
    Set cover = GetComp("07_top_cover_ring")
    Set port = GetComp("08_top_port")
    Set stylet = GetComp("09_stylet")
    Set baseComp = GetComp("10_sliding_base")
    If housing Is Nothing Or hub Is Nothing Or shaft Is Nothing Or nut Is Nothing Then
        MsgBox "Could not find the needle components (names 01_housing ... 10_sliding_base).", vbExclamation
        Exit Sub
    End If

    ' --- fixed / floating ----------------------------------------------------
    SetFixed housing, True: SetFixed plug, True: SetFixed cover, True: SetFixed baseComp, True
    SetFixed hub, False: SetFixed shaft, False: SetFixed pawl, False
    SetFixed nut, False: SetFixed port, False: SetFixed stylet, False

    ' --- 03 cannula hub: rotates in the plug bore, axial position held ---------
    MateConcentric "Hub in plug bore", Cyl(hub, 5#, 0, 0), Cyl(plug, 5.3, 0, 0), False
    MatePlanes "Hub axial position", hub, housing

    ' --- 04 spiral shaft: rotates in the ledge bore, axial position held -------
    MateConcentric "Shaft in ledge bore", Cyl(shaft, 5#, 0, 0), Cyl(housing, 6#, 0, 0), False
    MatePlanes "Shaft axial position", shaft, housing

    ' --- 05 rocker pawl: on the carrier post, held in the drive position -------
    MateConcentric "Pawl on post", Cyl(pawl, 1.6, 12.2, 0), Cyl(shaft, 1.5, 12.2, 0), True
    MatePlanes "Pawl axial position", pawl, housing

    ' --- 06 push cap + drive nut: slides 30 mm, keyed against rotation ---------
    MateConcentric "Cap in housing (keyed)", Cyl(nut, 12#, 0, 0), Cyl(housing, 19#, 0, 0), True
    ' nut bottom (z 80) to ledge top (z 22): 58 at rest, 28 fully pushed
    MateLimit "Push stroke 30 mm", Pln(nut, -1, 80#), Pln(housing, 1, 22#), 58#, 28#, 58#

    ' --- screw: nut pins drive the 2-start spiral grooves, 50 mm lead, LH ------
    MateScrew "Spiral drive (nut-shaft)", Cyl(nut, 5.25, 0, 0), Cyl(shaft, 5#, 0, 0), 50#, False

    ' --- gear 1:1: shaft drives the hub through the pawl (push stroke) ---------
    MateGear "Ratchet drive (shaft-hub)", Cyl(shaft, 5#, 0, 0), Cyl(hub, 5#, 0, 0), True

    ' --- 08 top port: seated in the cap counterbore ---------------------------
    MateConcentric "Port in cap", Cyl(port, 4.4, 0, 0), Cyl(nut, 4.5, 0, 0), True
    MateCoincident "Port seated", Pln(port, -1, 141#), Pln(nut, 1, 141#)

    ' --- 09 stylet: hex key in the hub socket, turns with the cannula ---------
    MateConcentric "Stylet in cannula (keyed)", Cyl(stylet, 1.15, 0, 0), Cyl(hub, 1.195, 0, 0), True
    MateCoincident "Stylet seated", Pln(stylet, -1, 11#), Pln(hub, 1, 11#)

    swModel.ClearSelection2 True
    swModel.ForceRebuild3 False
    swModel.ViewZoomtofit2

    MsgBox nOK & " mates added, " & nFail & " failed." & vbCrLf & vbCrLf & report & vbCrLf & _
        "Check: drag the push cap down. Seen from the top the purple shaft must turn" & vbCrLf & _
        "CLOCKWISE with the nut pins staying in the grooves; if not, edit the screw mate" & vbCrLf & _
        "and toggle Reverse. The orange hub must turn the SAME way as the shaft (pawl stays" & vbCrLf & _
        "in its tooth gap); if not, edit the gear mate and toggle Reverse.", vbInformation, "Needle mates"
End Sub

' =============================================================================
' Lookup helpers
' =============================================================================
Function GetComp(key As String) As Object
    Dim v As Variant, i As Long
    v = swAssy.GetComponents(False)
    If IsEmpty(v) Then Exit Function
    For i = 0 To UBound(v)
        If InStr(1, v(i).Name2, key, vbTextCompare) > 0 Then
            Set GetComp = v(i): Exit Function
        End If
    Next i
    AddLog "component " & key & " not found", False
End Function

Sub SetFixed(comp As Object, fixIt As Boolean)
    If comp Is Nothing Then Exit Sub
    swModel.ClearSelection2 True
    comp.Select4 False, Nothing, False
    If fixIt Then swAssy.FixComponent Else swAssy.UnfixComponent
    swModel.ClearSelection2 True
End Sub

' Cylindrical face of the given radius whose axis is parallel to Z through (x, y).  mm in.
Function Cyl(comp As Object, r As Double, x As Double, y As Double) As Object
    Set Cyl = FindFace(comp, True, r, x, y, 0, 0)
    If Cyl Is Nothing Then AddLog "no R" & r & " cylinder on " & CompName(comp), False
End Function

' Planar face with normal +Z (nz = 1) or -Z (nz = -1) lying at height z.  mm in.
Function Pln(comp As Object, nz As Double, z As Double) As Object
    Set Pln = FindFace(comp, False, 0, 0, 0, nz, z)
    If Pln Is Nothing Then AddLog "no plane z=" & z & " on " & CompName(comp), False
End Function

Function FindFace(comp As Object, isCyl As Boolean, r As Double, x As Double, y As Double, _
                  nz As Double, z As Double) As Object
    If comp Is Nothing Then Exit Function
    Dim vB As Variant, vF As Variant, info As Variant, i As Long, j As Long
    Dim f As Object, s As Object, p As Variant, n As Variant
    vB = comp.GetBodies3(swSolidBody, info)
    If IsEmpty(vB) Then Exit Function
    For i = 0 To UBound(vB)
        vF = vB(i).GetFaces
        If Not IsEmpty(vF) Then
            For j = 0 To UBound(vF)
                Set f = vF(j)
                Set s = f.GetSurface
                If isCyl Then
                    If s.IsCylinder Then
                        p = s.CylinderParams      ' origin(3), axis(3), radius
                        If Abs(p(6) - r * MM) < TOL And Abs(p(0) - x * MM) < TOL _
                           And Abs(p(1) - y * MM) < TOL And Abs(Abs(p(5)) - 1) < 0.000001 Then
                            Set FindFace = f: Exit Function
                        End If
                    End If
                Else
                    If s.IsPlane Then
                        n = f.Normal
                        p = s.PlaneParams         ' normal(3), root point(3)
                        If Abs(n(2) - nz) < 0.000001 And Abs(p(5) - z * MM) < TOL Then
                            Set FindFace = f: Exit Function
                        End If
                    End If
                End If
            Next j
        End If
    Next i
End Function

' First reference plane of a component (= Front Plane, the XY plane at z = 0).
Function FrontPlane(comp As Object) As Object
    Dim feat As Object
    Set feat = comp.FirstFeature
    Do While Not feat Is Nothing
        If feat.GetTypeName2 = "RefPlane" Then Set FrontPlane = feat: Exit Function
        Set feat = feat.GetNextFeature
    Loop
End Function

Function CompName(comp As Object) As String
    If comp Is Nothing Then CompName = "(missing)" Else CompName = comp.Name2
End Function

' =============================================================================
' Selection -> entity array (same pattern as the SOLIDWORKS API examples)
' =============================================================================
Function SelectEntity(e As Object) As Boolean
    If e Is Nothing Then Exit Function
    If TypeName(e) = "IFeature" Or TypeName(e) = "Feature" Then
        SelectEntity = e.Select2(True, 0)
    Else
        Dim ent As Object
        Set ent = e
        SelectEntity = ent.Select4(True, Nothing)
    End If
End Function

Function PairFromSelection(mateName As String, e1 As Object, e2 As Object) As Variant
    swModel.ClearSelection2 True
    If e1 Is Nothing Or e2 Is Nothing Then
        AddLog mateName & ": geometry not found", False: Exit Function
    End If
    If Not SelectEntity(e1) Or Not SelectEntity(e2) Then
        AddLog mateName & ": could not select", False: Exit Function
    End If
    Dim arr(1) As Object
    Set arr(0) = swSelMgr.GetSelectedObject6(1, -1)
    Set arr(1) = swSelMgr.GetSelectedObject6(2, -1)
    PairFromSelection = arr
End Function

Sub Finish(mateName As String, data As Object)
    Dim feat As Object
    Set feat = swAssy.CreateMate(data)
    swModel.ClearSelection2 True
    If feat Is Nothing Then
        AddLog mateName, False
    Else
        On Error Resume Next
        feat.Name = mateName
        On Error GoTo 0
        AddLog mateName, True
    End If
End Sub

Sub AddLog(msg As String, ok As Boolean)
    If ok Then
        nOK = nOK + 1: report = report & "  OK    " & msg & vbCrLf
    Else
        nFail = nFail + 1: report = report & "  FAIL  " & msg & vbCrLf
    End If
End Sub

' =============================================================================
' Mate builders (IAssemblyDoc::CreateMateData / CreateMate)
' =============================================================================
Sub MateConcentric(mateName As String, e1 As Object, e2 As Object, lockRot As Boolean)
    Dim ents As Variant, d As Object
    ents = PairFromSelection(mateName, e1, e2)
    If IsEmpty(ents) Then Exit Sub
    Set d = swAssy.CreateMateData(swMateCONCENTRIC)
    d.EntitiesToMate = ents
    d.MateAlignment = swMateAlignCLOSEST
    If lockRot Then
        On Error Resume Next
        d.LockRotation = True
        On Error GoTo 0
    End If
    Finish mateName, d
End Sub

Sub MateCoincident(mateName As String, e1 As Object, e2 As Object)
    Dim ents As Variant, d As Object
    ents = PairFromSelection(mateName, e1, e2)
    If IsEmpty(ents) Then Exit Sub
    Set d = swAssy.CreateMateData(swMateCOINCIDENT)
    d.EntitiesToMate = ents
    d.MateAlignment = swMateAlignCLOSEST
    Finish mateName, d
End Sub

' Front Plane of comp coincident with Front Plane of ref: holds the current axial position.
Sub MatePlanes(mateName As String, comp As Object, ref As Object)
    MateCoincident mateName, FrontPlane(comp), FrontPlane(ref)
End Sub

Sub MateLimit(mateName As String, e1 As Object, e2 As Object, dist As Double, dMin As Double, dMax As Double)
    Dim ents As Variant, d As Object
    ents = PairFromSelection(mateName, e1, e2)
    If IsEmpty(ents) Then Exit Sub
    Set d = swAssy.CreateMateData(swMateDISTANCE)
    d.EntitiesToMate = ents
    d.MateAlignment = swMateAlignCLOSEST
    d.FlipDimension = False
    d.Distance = dist * MM
    d.MaximumDistance = dMax * MM
    d.MinimumDistance = dMin * MM
    Finish mateName, d
End Sub

Sub MateScrew(mateName As String, e1 As Object, e2 As Object, leadMM As Double, rev As Boolean)
    Dim ents As Variant, d As Object
    ents = PairFromSelection(mateName, e1, e2)
    If IsEmpty(ents) Then Exit Sub
    Set d = swAssy.CreateMateData(swMateSCREW)
    d.EntitiesToMate = ents
    If IsEmpty(swDistancePerRevolution) Then
        ' constant not in this SOLIDWORKS version's type library: use revolutions per metre
        d.RevolutionVal = 1# / (leadMM * MM)
        report = report & "  NOTE  screw mate set as revolutions per length; check it reads 50 mm/rev" & vbCrLf
    Else
        d.RevolutionType = swDistancePerRevolution
        d.RevolutionVal = leadMM * MM
    End If
    d.Reverse = rev
    Finish mateName, d
End Sub

Sub MateGear(mateName As String, e1 As Object, e2 As Object, rev As Boolean)
    Dim ents As Variant, d As Object
    ents = PairFromSelection(mateName, e1, e2)
    If IsEmpty(ents) Then Exit Sub
    Set d = swAssy.CreateMateData(swMateGEAR)
    d.EntitiesToMate = ents
    d.GearRatioNumerator = 0.01
    d.GearRatioDenominator = 0.01
    d.Reverse = rev
    Finish mateName, d
End Sub
