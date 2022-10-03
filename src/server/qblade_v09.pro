# -------------------------------------------------
# Project created by David Marten using QtCreator
# -------------------------------------------------

# switch here to build either for 32bit or 64bit
CONFIG += build64bit

#the current version numbers
        DEFINES += version_string=\"\\\"x.x.x\\\"\"
win32:  DEFINES += compiled_string=\"\\\"64bit-windows-release\\\"\"
unix:   DEFINES += compiled_string=\"\\\"64bit-linux-release\\\"\"
        DEFINES += chrono_string=\"\\\"6.0.0\\\"\"

# specify which Qt modules are needed.
QT += core gui widgets opengl xml testlib

# set the name of the executable
TARGET = QBlade

# The template to use for the project. This determines wether the output will be an application or library
#TEMPLATE = app
TEMPLATE = lib
DEFINES += QBLADE_LIBRARY=true

# This toggles the license check functionality
#DEFINES += QBLADE_LICENSE
#CONFIG += QBLADE_LICENSE=true

# include the resources file into the binary
RESOURCES += qblade.qrc

# set the icon of the executable application file
win32:RC_ICONS = images/qblade.ico

# from gcc 4.8.1 on the c++11 implementation is feature complete
QMAKE_CXXFLAGS += -std=gnu++11  # usually it would be fine to give c++11 but the OpenCL part apparently needs gnu extensions
#QMAKE_CXXFLAGS += -fpermissive
# fixes the "too many sections" issue when compiling debug build under windows
win32:QMAKE_CXXFLAGS += -Wa,-mbig-ob
win32:QMAKE_CXXFLAGS += -w

# activate compiler support for openMP
QMAKE_CXXFLAGS += -fopenmp
LIBS += -fopenmp

# add the proper include path for libraries
win32: LIBS += -L$$PWD/libraries/libs_windows_64bit
unix:  LIBS += -L$$PWD/libraries/libs_unix_64bit

# includes QGLViewer
INCLUDEPATH += include_headers/QGLViewer

win32: LIBS += -lQGLViewer2
unix:  LIBS += -lQGLViewer

# include openGL & glu
win32: LIBS += -lopengl32 -lglu32
unix:  LIBS += -lGLU

# include openCL
win32: INCLUDEPATH += include_headers/OpenCL/win
unix:  INCLUDEPATH += include_headers/OpenCL/unix
       LIBS += -lOpenCL

# include path to Eigen headers
INCLUDEPATH += include_headers

# include Project Chrono
win32: LIBS += -llibChronoEngine
unix:  LIBS += -lChronoEngine

INCLUDEPATH += include_headers/Chrono
INCLUDEPATH += include_headers/Chrono/chrono
INCLUDEPATH += include_headers/Chrono/chrono/physics
INCLUDEPATH += include_headers/Chrono/chrono/collision
INCLUDEPATH += include_headers/Chrono/chrono/collision/bullet

# include Lapack
win32: INCLUDEPATH += include_headers/Lapack/win
win32: LIBS += -lliblapacke

unix: INCLUDEPATH += include_headers/Lapack/unix
unix: LIBS += -llapacke
unix: LIBS += -llapacke
unix: LIBS += -llapack
unix: LIBS += -lblas
unix: LIBS += -lgfortran
unix: LIBS += -ltmglib

# include clBlast
INCLUDEPATH += include_headers/CLBlast
win32: LIBS += -llibclblast
unix:  LIBS += -lclblast

# include LicenseCC
QBLADE_LICENSE
{
# INCLUDEPATH += include_headers/LicenseCC
# unix: LIBS += -llicense
# unix: LIBS += -lcrypto

 win32: LIBS += liblicense
 win32: LIBS += libiphlpapi
 win32: LIBS += -lbcrypt
}

SOURCES += src/MainFrame.cpp \
    src/DebugDialog.cpp \
    src/IceThrowSimulation/IceParticle.cpp \
    src/ImportExport.cpp \
    src/Main.cpp \
    src/Globals.cpp \
    src/Misc/EnvironmentDialog.cpp \
    src/QControl/TurbineInputs.cpp \
    src/QSimulation/QSimulationDock.cpp \
    src/QSimulation/QSimulationMenu.cpp \
    src/QSimulation/QSimulationModule.cpp \
    src/QSimulation/QSimulationToolBar.cpp \
    src/QSimulation/QSimulationTwoDContextMenu.cpp \
    src/QTurbine/QMultiTurbineCreatorDialog.cpp \
    src/StructModel/ChBodyAddedMass.cpp \
    src/StructModel/ChNodeFEAxyzrotAddedMass.cpp \
    src/StructModel/ChVariablesBodyAddedMass.cpp \
    src/TwoDWidget.cpp \
    src/GLWidget.cpp \
    src/Misc/GLLightDlg.cpp \
    src/VortexObjects/VortexPanel.cpp \
    src/Waves/LinearWave.cpp \
    src/Waves/WaveCreatorDialog.cpp \
    src/Waves/WaveDock.cpp \
    src/Waves/WaveMenu.cpp \
    src/Waves/WaveModule.cpp \
    src/Waves/WaveToolBar.cpp \
    src/Waves/WaveTwoDContextMenu.cpp \
    src/XDirect/BatchDlg.cpp \
    src/XDirect/BatchThreadDlg.cpp \
    src/XDirect/XFoilTask.cpp \
    src/XDirect/CAddDlg.cpp \
    src/XDirect/FoilCoordDlg.cpp \
    src/XDirect/FoilGeomDlg.cpp \
    src/XDirect/FoilPolarDlg.cpp \
    src/XDirect/FlapDlg.cpp \
    src/XDirect/InterpolateFoilsDlg.cpp \
    src/XDirect/LEDlg.cpp \
    src/XDirect/ManageFoilsDlg.cpp \
    src/XDirect/NacaFoilDlg.cpp \
    src/XDirect/ReListDlg.cpp \
    src/XDirect/TEGapDlg.cpp \
    src/XDirect/TwoDPanelDlg.cpp \
    src/XDirect/XDirectStyleDlg.cpp \
    src/XDirect/XFoil.cpp \
    src/XDirect/XFoilAnalysisDlg.cpp \
    src/XDirect/XFoilAdvancedDlg.cpp \
    src/XDirect/XDirect.cpp \
    src/Objects/CVector.cpp \
    src/Objects/Foil.cpp \
    src/Objects/OpPoint.cpp \
    src/Objects/Polar.cpp \
    src/Objects/Quaternion.cpp \
    src/Objects/Sf.cpp \
    src/Objects/Spline.cpp \
    src/Misc/EditPlrDlg.cpp \
    src/Misc/PolarFilterDlg.cpp \
    src/Misc/TranslatorDlg.cpp \
    src/Misc/UnitsDlg.cpp \
    src/Misc/LinePickerDlg.cpp \
    src/Misc/LineDelegate.cpp \
    src/Misc/LineCbBox.cpp \
    src/Misc/LineButton.cpp \
    src/Misc/FloatEditDelegate.cpp \
    src/Misc/DisplaySettingsDlg.cpp \
    src/Misc/ColorButton.cpp \
    src/Misc/ObjectPropsDlg.cpp \
    src/Graph/QGraph.cpp \
    src/Graph/GraphWidget.cpp \
    src/Graph/GraphDlg.cpp \
    src/Graph/Graph.cpp \
    src/Graph/Curve.cpp \
    src/XInverse/FoilSelectionDlg.cpp \
    src/XInverse/PertDlg.cpp \
    src/XInverse/XInverse.cpp \
    src/XInverse/InverseOptionsDlg.cpp \
    src/Design/FoilTableDelegate.cpp \
    src/Design/AFoilGridDlg.cpp \
    src/Design/LECircleDlg.cpp \
    src/Design/AFoil.cpp \
    src/Design/SplineCtrlsDlg.cpp \
    src/Design/AFoilTableDlg.cpp \
    src/QBEM/TData.cpp \
    src/QBEM/TBEMData.cpp \
    src/QBEM/SimuWidget.cpp \
    src/QBEM/OptimizeDlg.cpp \
    src/QBEM/Edit360PolarDlg.cpp \
    src/QBEM/CreateBEMDlg.cpp \
    src/QBEM/BladeScaleDlg.cpp \
    src/QBEM/BEMData.cpp \
    src/QBEM/BEM.cpp \
    src/QBEM/BData.cpp \
    src/QBEM/Blade.cpp \
    src/Objects/Surface.cpp \
    src/QBEM/BladeDelegate.cpp \
    src/QBEM/BladeAxisDelegate.cpp \
    src/QBEM/CBEMData.cpp \
    src/QBEM/PrescribedValuesDlg.cpp \
    src/QBEM/CircularFoilDlg.cpp \
    src/QBEM/BEMSimDock.cpp \
    src/QBEM/BEMDock.cpp \
    src/QDMS/DMS.cpp \
    src/QDMS/SimuWidgetDMS.cpp \
    src/QDMS/BladeDelegateVAWT.cpp \
    src/QDMS/OptimizeDlgVAWT.cpp \
    src/QDMS/BladeScaleDlgVAWT.cpp \
    src/QDMS/CreateDMSDlg.cpp \
    src/QDMS/DMSData.cpp \
    src/QDMS/DData.cpp \
    src/QDMS/TDMSData.cpp \
    src/QDMS/DMSSimDock.cpp \
    src/QDMS/DMSDock.cpp \
    src/QDMS/CDMSData.cpp \
    src/Windfield/WindField.cpp \
    src/XWidgets.cpp \
    src/Windfield/WindFieldModule.cpp \
    src/Module.cpp \
    src/Windfield/WindFieldToolBar.cpp \
    src/ScrolledDock.cpp \
    src/Store.cpp \
    src/Windfield/WindFieldMenu.cpp \
    src/QFem/taperedelem.cpp \
    src/QFem/structintegrator.cpp \
    src/QFem/structelem.cpp \
    src/QFem/node.cpp \
    src/QFem/eqnmotion.cpp \
    src/QFem/clipper.cpp \
    src/QFem/unitvector.cpp \
    src/QFem/mode.cpp \
    src/QFem/deformationvector.cpp \
    src/QFem/QFEMDock.cpp \
    src/QFem/QFEMToolBar.cpp \
    src/QFem/QFEMModule.cpp \
    src/QFem/QFEMMenu.cpp \
    src/QFem/StructDelegate.cpp \
    src/QFem/BladeStructure.cpp \
    src/StorableObject.cpp \
    src/QBEM/BEMToolbar.cpp \
    src/QDMS/DMSToolbar.cpp \
    src/QBEM/360Polar.cpp \
    src/Misc/NumberEdit.cpp \
    src/Serializer.cpp \
    src/StoreAssociatedComboBox.cpp \
    src/GlobalFunctions.cpp \
    src/Misc/SignalBlockerInterface.cpp \
    src/Graph/NewGraph.cpp \
    src/Graph/Axis.cpp \
    src/Graph/NewCurve.cpp \
    src/Graph/GraphOptionsDialog.cpp \
    src/Graph/ShowAsGraphInterface.cpp \
    src/QFem/QFEMTwoDContextMenu.cpp \
    src/QFem/forcingterm.cpp \
    src/QFem/staticequation.cpp \
    src/QFem/BladeStructureLoading.cpp \
    src/QBEM/ExportGeomDlg.cpp \
    src/TwoDContextMenu.cpp \
    src/Misc/FixedSizeLabel.cpp \
    src/QBladeApplication.cpp \
    src/VortexObjects/VortexNode.cpp \
    src/VortexObjects/VortexLine.cpp \
    src/VortexObjects/DummyLine.cpp \
    src/QBEM/PolarSelectionDialog.cpp \
    src/SimulationDock.cpp \
    src/CreatorDock.cpp \
    src/SimulationModule.cpp \
    src/SimulationToolBar.cpp \
    src/ColorManager.cpp \
    src/Misc/LineStyleButton.cpp \
    src/Misc/LineStyleDialog.cpp \
    src/Misc/LineStyleComboBox.cpp \
    src/Misc/NewColorButton.cpp \
    src/TwoDGraphMenu.cpp \
    src/Windfield/WindFieldCreatorDialog.cpp \
    src/ParameterViewer.cpp \
    src/ParameterObject.cpp \
    src/ParameterGrid.cpp \
    src/TwoDWidgetInterface.cpp \
    src/Windfield/WindFieldDock.cpp \
    src/CreatorDialog.cpp \
    src/SimulationCreatorDialog.cpp \
    src/Noise/NoiseModule.cpp \
    src/Noise/NoiseSimulation.cpp \
    src/Noise/NoiseToolBar.cpp \
    src/Noise/NoiseDock.cpp \
    src/CreatorTwoDDock.cpp \
    src/Noise/NoiseCreatorDialog.cpp \
    src/Noise/NoiseOpPoint.cpp \
    src/Noise/NoiseCalculation.cpp \
    src/Noise/NoiseParameter.cpp \
    src/Noise/NoiseException.cpp \
    src/Noise/NoiseContextMenu.cpp \
    src/Noise/NoiseMenu.cpp \
    src/QDMS/StrutCreatorDialog.cpp \
    src/QDMS/Strut.cpp \
    src/QBladeCMDApplication.cpp \
    src/QDMS/VawtDesignModule.cpp \
    src/QDMS/VawtDesignToolBar.cpp \
    src/QDMS/VawtDesignDock.cpp \
    src/GLMenu.cpp \
    src/QBEM/BladeWrapperModel.cpp \
    src/Misc/NumberEditDelegate.cpp \
    src/Misc/ComboBoxDelegate.cpp \
    src/Objects/CVectorf.cpp \
    src/StructModel/StrElem.cpp \
    src/StructModel/StrNode.cpp \
    src/Misc/MultiPolarDialog.cpp \
    src/Misc/MultiPolarDelegate.cpp \
    src/QDMS/NewStrutCreatorDialog.cpp \
    src/QDMS/BatchEditDialog.cpp \
    src/QDMS/CustomShapeDialog.cpp \
    src/IntegrationTest/integrationtest.cpp \
    src/QDMS/VawtDesignMenu.cpp \
    src/MultiSimulation/CommonMultiSimulationModule.cpp \
    src/MultiSimulation/BemMultiSimulationModule.cpp \
    src/MultiSimulation/CommonMultiSimulationDock.cpp \
    src/MultiSimulation/BemMultiSimulationDock.cpp \
    src/MultiSimulation/CommonMultiSimulationToolBar.cpp \
    src/MultiSimulation/BemMultiSimulationToolBar.cpp \
    src/MultiSimulation/CommonMultiSimulationCreatorDialog.cpp \
    src/MultiSimulation/BemMultiSimulationCreatorDialog.cpp \
    src/MultiSimulation/CommonMultiSimulationContextMenu.cpp \
    src/MultiSimulation/BemMultiSimulationContextMenu.cpp \
    src/MultiSimulation/DmsMultiSimulationContextMenu.cpp \
    src/MultiSimulation/DmsMultiSimulationModule.cpp \
    src/MultiSimulation/DmsMultiSimulationCreatorDialog.cpp \
    src/MultiSimulation/DmsMultiSimulationDock.cpp \
    src/MultiSimulation/DmsMultiSimulationToolBar.cpp \
    src/RotorSimulation/CommonRotorSimulationModule.cpp \
    src/RotorSimulation/CommonRotorSimulationToolBar.cpp \
    src/RotorSimulation/CommonRotorSimulationDock.cpp \
    src/RotorSimulation/CommonRotorSimulationCreatorDialog.cpp \
    src/RotorSimulation/CommonRotorSimulationContextMenu.cpp \
    src/RotorSimulation/BemRotorSimulationContextMenu.cpp \
    src/RotorSimulation/DmsRotorSimulationContextMenu.cpp \
    src/RotorSimulation/BemRotorSimulationDock.cpp \
    src/RotorSimulation/DmsRotorSimulationDock.cpp \
    src/RotorSimulation/BemRotorSimulationToolBar.cpp \
    src/RotorSimulation/DmsRotorSimulationToolBar.cpp \
    src/RotorSimulation/BemRotorSimulationModule.cpp \
    src/RotorSimulation/DmsRotorSimulationModule.cpp \
    src/RotorSimulation/BemRotorSimulationCreatorDialog.cpp \
    src/RotorSimulation/DmsRotorSimulationCreatorDialog.cpp \
    src/TurbineSimulation/CommonTurbineSimulationModule.cpp \
    src/TurbineSimulation/BemTurbineSimulationModule.cpp \
    src/TurbineSimulation/DmsTurbineSimulationModule.cpp \
    src/TurbineSimulation/CommonTurbineSimulationDock.cpp \
    src/TurbineSimulation/BemTurbineSimulationDock.cpp \
    src/TurbineSimulation/DmsTurbineSimulationDock.cpp \
    src/TurbineSimulation/CommonTurbineDock.cpp \
    src/TurbineSimulation/BemTurbineDock.cpp \
    src/TurbineSimulation/DmsTurbineDock.cpp \
    src/TurbineSimulation/CommonTurbineSimulationContextMenu.cpp \
    src/TurbineSimulation/BemTurbineSimulationContextMenu.cpp \
    src/TurbineSimulation/DmsTurbineSimulationContextMenu.cpp \
    src/TurbineSimulation/CommonTurbineSimulationToolBar.cpp \
    src/TurbineSimulation/BemTurbineSimulationToolBar.cpp \
    src/TurbineSimulation/DmsTurbineSimulationToolBar.cpp \
    src/TurbineSimulation/CommonTurbineSimulationCreatorDialog.cpp \
    src/TurbineSimulation/BemTurbineSimulationCreatorDialog.cpp \
    src/TurbineSimulation/DmsTurbineSimulationCreatorDialog.cpp \
    src/TurbineSimulation/CommonTurbineCreatorDialog.cpp \
    src/TurbineSimulation/BemTurbineCreatorDialog.cpp \
    src/TurbineSimulation/DmsTurbineCreatorDialog.cpp \
    src/QBEM/AFC.cpp \
    src/QBEM/DynPolarSet.cpp \
    src/QBEM/DynPolarSetDialog.cpp \
    src/QBEM/FlapCreatorDialog.cpp \
    src/VortexObjects/VortexParticle.cpp \
    src/StructModel/PID.cpp \
    src/QControl/QControl.cpp \
    src/StructModel/CoordSys.cpp \
    src/IceThrowSimulation/IceThrowSimulation.cpp \
    src/QTurbine/QTurbineModule.cpp \
    src/QTurbine/QTurbineDock.cpp \
    src/QTurbine/QTurbineToolBar.cpp \
    src/QTurbine/QTurbine.cpp \
    src/QTurbine/QTurbineCreatorDialog.cpp \
    src/QTurbine/QTurbineTwoDContextMenu.cpp \
    src/QSimulation/QSimulation.cpp \
    src/QSimulation/QSimulationCreatorDialog.cpp \
    src/StructModel/StrModel.cpp \
    src/StructModel/StrObjects.cpp \
    src/QTurbine/QTurbineSimulationData.cpp \
    src/QTurbine/QTurbineResults.cpp \
    src/QTurbine/QTurbineGlRendering.cpp \
    src/OpenCLSetup.cpp \
    src/FlightSimulator/Plane.cpp \
    src/FlightSimulator/PlaneDesignerDock.cpp \
    src/FlightSimulator/PlaneDesignerModule.cpp \
    src/FlightSimulator/PlaneDesignerToolbar.cpp \
    src/FlightSimulator/QFlightDock.cpp \
    src/FlightSimulator/QFlightModule.cpp \
    src/FlightSimulator/QFlightSimCreatorDialog.cpp \
    src/FlightSimulator/QFlightSimulation.cpp \
    src/FlightSimulator/QFlightStructuralModel.cpp \
    src/FlightSimulator/QFlightToolBar.cpp \
    src/FlightSimulator/QFlightTwoDContextMenu.cpp \
    src/FlightSimulator/WingDelegate.cpp \
    src/FlightSimulator/WingDesignerDock.cpp \
    src/FlightSimulator/WingDesignerModule.cpp \
    src/FlightSimulator/WingDesignerToolbar.cpp \
    src/InterfaceDll/QBladeDLLApplication.cpp \
    src/InterfaceDll/QBladeDLLInclude.cpp \
    src/QSimulation/QVelocityCutPlane.cpp \
    src/QBEM/Interpolate360PolarsDlg.cpp \
    src/DLCPrep/DLCDefinition.cpp \
    src/DLCPrep/DLCSetupDialog.cpp \
    src/Windfield/WindFieldProgressDialog.cpp \
    src/Windfield/WindFieldTwoDContextMenu.cpp \
    src/QTurbine/QTurbineMenu.cpp

HEADERS += src/MainFrame.h \
    src/DebugDialog.h \
    src/IceThrowSimulation/IceParticle.h \
    src/ImportExport.h \
    src/Misc/EnvironmentDialog.h \
    src/Params.h \
    src/Globals.h \
    src/QControl/TurbineInputs.h \
    src/QSimulation/QSimulationDock.h \
    src/QSimulation/QSimulationMenu.h \
    src/QSimulation/QSimulationModule.h \
    src/QSimulation/QSimulationToolBar.h \
    src/QSimulation/QSimulationTwoDContextMenu.h \
    src/QTurbine/QMultiTurbineCreatorDialog.h \
    src/StructModel/ChBodyAddedMass.h \
    src/StructModel/ChNodeFEAxyzrotAddedMass.h \
    src/StructModel/ChVariablesBodyAddedMass.h \
    src/TwoDWidget.h \
    src/GLWidget.h \
    src/Misc/GLLightDlg.h \
    src/VortexObjects/VortexPanel.h \
    src/Waves/LinearWave.h \
    src/Waves/WaveCreatorDialog.h \
    src/Waves/WaveDock.h \
    src/Waves/WaveMenu.h \
    src/Waves/WaveModule.h \
    src/Waves/WaveToolBar.h \
    src/Waves/WaveTwoDContextMenu.h \
    src/XDirect/XFoil.h \
    src/XDirect/XFoilAnalysisDlg.h \
    src/XDirect/XFoilAdvancedDlg.h \
    src/XDirect/XDirect.h \
    src/XDirect/TwoDPanelDlg.h \
    src/XDirect/TEGapDlg.h \
    src/XDirect/InterpolateFoilsDlg.h \
    src/XDirect/FoilGeomDlg.h \
    src/XDirect/FoilCoordDlg.h \
    src/XDirect/ReListDlg.h \
    src/XDirect/XDirectStyleDlg.h \
    src/XDirect/ManageFoilsDlg.h \
    src/XDirect/NacaFoilDlg.h \
    src/XDirect/LEDlg.h \
    src/XDirect/FoilPolarDlg.h \
    src/XDirect/FlapDlg.h \
    src/XDirect/CAddDlg.h \
    src/XDirect/BatchDlg.h \
    src/XDirect/BatchThreadDlg.h \
    src/XDirect/XFoilTask.h \
    src/XInverse/XInverse.h \
    src/XInverse/InverseOptionsDlg.h \
    src/XInverse/FoilSelectionDlg.h \
    src/XInverse/PertDlg.h \
    src/Objects/Surface.h \
    src/Objects/Spline.h \
    src/Objects/Sf.h \
    src/Objects/OpPoint.h \
    src/Objects/Quaternion.h \
    src/Objects/Polar.h \
    src/Objects/CVector.h \
    src/Objects/Foil.h \
    src/Misc/PolarFilterDlg.h \
    src/Misc/TranslatorDlg.h \
    src/Misc/UnitsDlg.h \
    src/Misc/LinePickerDlg.h \
    src/Misc/LineDelegate.h \
    src/Misc/FloatEditDelegate.h \
    src/Misc/DisplaySettingsDlg.h \
    src/Misc/ColorButton.h \
    src/Misc/LineCbBox.h \
    src/Misc/LineButton.h \
    src/Misc/EditPlrDlg.h \
    src/Misc/ObjectPropsDlg.h \
    src/Graph/GraphWidget.h \
    src/Graph/Graph.h \
    src/Graph/GraphDlg.h \
    src/Graph/Curve.h \
    src/Graph/QGraph.h \
    src/Design/AFoil.h \
    src/Design/AFoilGridDlg.h \
    src/Design/LECircleDlg.h \
    src/Design/SplineCtrlsDlg.h \
    src/Design/FoilTableDelegate.h \
    src/Design/AFoilTableDlg.h \
    src/QBEM/TData.h \
    src/QBEM/TBEMData.h \
    src/QBEM/SimuWidget.h \
    src/QBEM/OptimizeDlg.h \
    src/QBEM/Edit360PolarDlg.h \
    src/QBEM/CreateBEMDlg.h \
    src/QBEM/BladeScaleDlg.h \
    src/QBEM/BEMData.h \
    src/QBEM/BEM.h \
    src/QBEM/BData.h \
    src/QBEM/Blade.h \
    src/QBEM/BladeDelegate.h \
    src/QBEM/BladeAxisDelegate.h \
    src/QBEM/CBEMData.h \
    src/QBEM/PrescribedValuesDlg.h \
    src/QBEM/CircularFoilDlg.h \
    src/QBEM/BEMSimDock.h \
    src/QBEM/BEMDock.h \
    src/QDMS/DMS.h \
    src/QDMS/SimuWidgetDMS.h \
    src/QDMS/BladeDelegateVAWT.h \
    src/QDMS/OptimizeDlgVAWT.h \
    src/QDMS/BladeScaleDlgVAWT.h \
    src/QDMS/CreateDMSDlg.h \
    src/QDMS/DMSData.h \
    src/QDMS/DData.h \
    src/QDMS/TDMSData.h \
    src/QDMS/DMSSimDock.h \
    src/QDMS/DMSDock.h \
    src/QDMS/CDMSData.h \
    src/Windfield/WindField.h \
    src/XWidgets.h \
    src/Windfield/WindFieldModule.h \
    src/Module.h \
    src/Windfield/WindFieldToolBar.h \
    src/ScrolledDock.h \
    src/Store.h \
    src/Windfield/WindFieldMenu.h \
    src/QFem/taperedelem.h \
    src/QFem/structintegrator.h \
    src/QFem/structelem.h \
    src/QFem/node.h \
    src/QFem/eqnmotion.h \
    src/QFem/clipper.cpp \
    src/QFem/unitvector.h \
    src/QFem/mode.h \
    src/QFem/deformationvector.h \
    src/QFem/QFEMDock.h \
    src/QFem/QFEMToolBar.h \
    src/QFem/QFEMModule.h \
    src/QFem/QFEMMenu.h \
    src/QFem/BladeStructure.h \
    src/QFem/StructDelegate.h \
    src/StorableObject.h \
    src/QBEM/BEMToolbar.h \
    src/QDMS/DMSToolbar.h \
    src/QBEM/360Polar.h \
    src/Misc/NumberEdit.h \
    src/Serializer.h \
    src/StoreAssociatedComboBox.h \
    src/StoreAssociatedComboBox_include.h \
    src/Store_include.h \
    src/StorableObject_heirs.h \
    src/GlobalFunctions.h \
    src/Misc/SignalBlockerInterface.h \
    src/Graph/NewGraph.h \
    src/Graph/Axis.h \
    src/Graph/NewCurve.h \
    src/Graph/GraphOptionsDialog.h \
    src/Graph/ShowAsGraphInterface.h \
    src/QFem/QFEMTwoDContextMenu.h \
    src/QFem/forcingterm.h \
    src/QFem/staticequation.h \
    src/QFem/BladeStructureLoading.h \
    src/QBEM/ExportGeomDlg.h \
    src/TwoDContextMenu.h \
    src/Misc/FixedSizeLabel.h \
    src/QBladeApplication.h \
    src/VortexObjects/VortexNode.h \
    src/VortexObjects/VortexLine.h \
    src/VortexObjects/DummyLine.h \
    src/QBEM/PolarSelectionDialog.h \
    src/SimulationDock.h \
    src/CreatorDock.h \
    src/SimulationModule.h \
    src/SimulationToolBar.h \
    src/ColorManager.h \
    src/Misc/LineStyleButton.h \
    src/Misc/LineStyleDialog.h \
    src/Misc/LineStyleComboBox.h \
    src/Misc/NewColorButton.h \
    src/TwoDGraphMenu.h \
    src/Windfield/WindFieldCreatorDialog.h \
    src/ParameterViewer.h \
    src/ParameterObject.h \
    src/ParameterGrid.h \
    src/ParameterKeys.h \
    src/TwoDWidgetInterface.h \
    src/Windfield/WindFieldDock.h \
    src/CreatorDialog.h \
    src/SimulationCreatorDialog.h \
    src/Noise/NoiseModule.h \
    src/Noise/NoiseSimulation.h \
    src/Noise/NoiseToolBar.h \
    src/Noise/NoiseDock.h \
    src/CreatorTwoDDock.h \
    src/Noise/NoiseCreatorDialog.h \
    src/Noise/NoiseOpPoint.h \
    src/Noise/NoiseCalculation.h \
    src/Noise/NoiseParameter.h \
    src/Noise/NoiseException.h \
    src/Noise/NoiseContextMenu.h \
    src/Noise/NoiseMenu.h \
    src/QDMS/StrutCreatorDialog.h \
    src/QDMS/Strut.h \
    src/QBladeCMDApplication.h \
    src/QDMS/VawtDesignModule.h \
    src/QDMS/VawtDesignToolBar.h \
    src/QDMS/VawtDesignDock.h \
    src/GLMenu.h \
    src/QBEM/BladeWrapperModel.h \
    src/Misc/NumberEditDelegate.h \
    src/Misc/ComboBoxDelegate.h \
    src/Objects/CVectorf.h \
    src/StructModel/StrElem.h \
    src/StructModel/StrNode.h \
    src/Misc/MultiPolarDialog.h \
    src/Misc/MultiPolarDelegate.h \
    src/QDMS/NewStrutCreatorDialog.h \
    src/QDMS/BatchEditDialog.h \
    src/QDMS/CustomShapeDialog.h \
    src/IntegrationTest/integrationtest.h \
    src/CompileSettings.h \
    src/QDMS/VawtDesignMenu.h \
    src/MultiSimulation/CommonMultiSimulationModule.h \
    src/MultiSimulation/BemMultiSimulationModule.h \
    src/MultiSimulation/CommonMultiSimulationDock.h \
    src/MultiSimulation/BemMultiSimulationDock.h \
    src/MultiSimulation/CommonMultiSimulationToolBar.h \
    src/MultiSimulation/BemMultiSimulationToolBar.h \
    src/MultiSimulation/CommonMultiSimulationCreatorDialog.h \
    src/MultiSimulation/BemMultiSimulationCreatorDialog.h \
    src/MultiSimulation/CommonMultiSimulationContextMenu.h \
    src/MultiSimulation/BemMultiSimulationContextMenu.h \
    src/MultiSimulation/DmsMultiSimulationContextMenu.h \
    src/MultiSimulation/DmsMultiSimulationModule.h \
    src/MultiSimulation/DmsMultiSimulationCreatorDialog.h \
    src/MultiSimulation/DmsMultiSimulationDock.h \
    src/MultiSimulation/DmsMultiSimulationToolBar.h \
    src/RotorSimulation/CommonRotorSimulationModule.h \
    src/RotorSimulation/CommonRotorSimulationToolBar.h \
    src/RotorSimulation/CommonRotorSimulationDock.h \
    src/RotorSimulation/CommonRotorSimulationCreatorDialog.h \
    src/RotorSimulation/CommonRotorSimulationContextMenu.h \
    src/RotorSimulation/BemRotorSimulationContextMenu.h \
    src/RotorSimulation/DmsRotorSimulationContextMenu.h \
    src/RotorSimulation/BemRotorSimulationDock.h \
    src/RotorSimulation/DmsRotorSimulationDock.h \
    src/RotorSimulation/BemRotorSimulationToolBar.h \
    src/RotorSimulation/DmsRotorSimulationToolBar.h \
    src/RotorSimulation/BemRotorSimulationModule.h \
    src/RotorSimulation/DmsRotorSimulationModule.h \
    src/RotorSimulation/BemRotorSimulationCreatorDialog.h \
    src/RotorSimulation/DmsRotorSimulationCreatorDialog.h \
    src/TurbineSimulation/CommonTurbineSimulationModule.h \
    src/TurbineSimulation/BemTurbineSimulationModule.h \
    src/TurbineSimulation/DmsTurbineSimulationModule.h \
    src/TurbineSimulation/CommonTurbineSimulationDock.h \
    src/TurbineSimulation/BemTurbineSimulationDock.h \
    src/TurbineSimulation/DmsTurbineSimulationDock.h \
    src/TurbineSimulation/CommonTurbineDock.h \
    src/TurbineSimulation/BemTurbineDock.h \
    src/TurbineSimulation/DmsTurbineDock.h \
    src/TurbineSimulation/CommonTurbineSimulationContextMenu.h \
    src/TurbineSimulation/BemTurbineSimulationContextMenu.h \
    src/TurbineSimulation/DmsTurbineSimulationContextMenu.h \
    src/TurbineSimulation/CommonTurbineSimulationToolBar.h \
    src/TurbineSimulation/BemTurbineSimulationToolBar.h \
    src/TurbineSimulation/DmsTurbineSimulationToolBar.h \
    src/TurbineSimulation/CommonTurbineSimulationCreatorDialog.h \
    src/TurbineSimulation/BemTurbineSimulationCreatorDialog.h \
    src/TurbineSimulation/DmsTurbineSimulationCreatorDialog.h \
    src/TurbineSimulation/CommonTurbineCreatorDialog.h \
    src/TurbineSimulation/BemTurbineCreatorDialog.h \
    src/TurbineSimulation/DmsTurbineCreatorDialog.h \
    src/QBEM/AFC.h \
    src/QBEM/DynPolarSet.h \
    src/QBEM/DynPolarSetDialog.h \
    src/QBEM/FlapCreatorDialog.h \
    src/VortexObjects/VortexParticle.h \
    src/StructModel/PID.h \
    src/QControl/QControl.h \
    src/StructModel/CoordSys.h \
    src/IceThrowSimulation/IceThrowSimulation.h \
    src/QTurbine/QTurbineModule.h \
    src/QTurbine/QTurbineDock.h \
    src/QTurbine/QTurbineToolBar.h \
    src/QTurbine/QTurbine.h \
    src/QTurbine/QTurbineCreatorDialog.h \
    src/QTurbine/QTurbineTwoDContextMenu.h \
    src/QSimulation/QSimulation.h \
    src/QSimulation/QSimulationCreatorDialog.h \
    src/StructModel/StrModel.h \
    src/StructModel/StrObjects.h \
    src/QTurbine/QTurbineSimulationData.h \
    src/QTurbine/QTurbineResults.h \
    src/QTurbine/QTurbineGlRendering.h \
    src/QSimulation/QSimulationThread.h \
    src/OpenCLSetup.h \
    src/FlightSimulator/Plane.h \
    src/FlightSimulator/PlaneDesignerDock.h \
    src/FlightSimulator/PlaneDesignerModule.h \
    src/FlightSimulator/PlaneDesignerToolbar.h \
    src/FlightSimulator/QFlightDock.h \
    src/FlightSimulator/QFlightModule.h \
    src/FlightSimulator/QFlightSimCreatorDialog.h \
    src/FlightSimulator/QFlightSimulation.h \
    src/FlightSimulator/QFlightStructuralModel.h \
    src/FlightSimulator/QFlightToolBar.h \
    src/FlightSimulator/QFlightTwoDContextMenu.h \
    src/FlightSimulator/WingDelegate.h \
    src/FlightSimulator/WingDesignerDock.h \
    src/FlightSimulator/WingDesignerModule.h \
    src/FlightSimulator/WingDesignerToolbar.h \
    src/InterfaceDll/QBladeDLLApplication.h \
    src/InterfaceDll/QBladeDLLInclude.h \
    src/QSimulation/QVelocityCutPlane.h \
    src/QBEM/Interpolate360PolarsDlg.h \
    src/DLCPrep/DLCDefinition.h \
    src/DLCPrep/DLCSetupDialog.h \
    src/Windfield/WindFieldProgressDialog.h \
    src/Windfield/WindFieldTwoDContextMenu.h \
    src/QTurbine/QTurbineMenu.h

QBLADE_LICENSE
{
 HEADERS += src/LicenseCheck.h
 SOURCES += src/LicenseCheck.cpp
}

#here a few usefull files and required binaries are automatically copied to the build directory

QMAKE_EXTRA_TARGETS += copyTarget
PRE_TARGETDEPS += copyTarget

    unix:createdirbinary.commands =  $(MKDIR) \"$$shell_path($$OUT_PWD\\Binaries)\"
    unix:copyTarget.depends += createdirbinary
    unix:QMAKE_EXTRA_TARGETS += createdirbinary

CONFIG(debug, debug|release) {

    win32:copybinaries.commands = $(COPY) \"$$shell_path($$PWD\\data\\Binaries\\win)\" \"$$shell_path($$OUT_PWD\\debug\Binaries)\"
    else:unix:copybinaries.commands = $(COPY_FILE) \"$$shell_path($$PWD\\data\\Binaries\\unix\\TurbSim64)\" \"$$shell_path($$OUT_PWD\\Binaries\\)\"
    copyTarget.depends += copybinaries
    QMAKE_EXTRA_TARGETS += copybinaries

    win32:copycontrollers.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\ControllerFiles)\" \"$$shell_path($$OUT_PWD\\debug\\ControllerFiles)\"
    unix:copycontrollers.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\ControllerFiles)\" \"$$shell_path($$OUT_PWD)\"
    copyTarget.depends += copycontrollers
    QMAKE_EXTRA_TARGETS += copycontrollers

    win32:copystructural.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\StructuralFiles)\" \"$$shell_path($$OUT_PWD\\debug\\StructuralFiles)\"
    unix:copystructural.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\StructuralFiles)\" \"$$shell_path($$OUT_PWD)\"
    copyTarget.depends += copystructural
    QMAKE_EXTRA_TARGETS += copystructural

    win32:copyprojects.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\CertTest)\" \"$$shell_path($$OUT_PWD\\debug\\CertTest)\"
    unix:copyprojects.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\CertTest)\" \"$$shell_path($$OUT_PWD)\"
    copyTarget.depends += copyprojects
    QMAKE_EXTRA_TARGETS += copyprojects
}
else {

    win32:copybinaries.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\Binaries\\win)\" \"$$shell_path($$OUT_PWD\\release\\Binaries)\"
    else:unix:copybinaries.commands = $(COPY_FILE) \"$$shell_path($$PWD\\data\\Binaries\\unix\\TurbSim64)\" \"$$shell_path($$OUT_PWD\\Binaries\\)\"
    copyTarget.depends += copybinaries
    QMAKE_EXTRA_TARGETS += copybinaries

    win32:copycontrollers.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\ControllerFiles)\" \"$$shell_path($$OUT_PWD\\release\\ControllerFiles)\"
    unix:copycontrollers.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\ControllerFiles)\" \"$$shell_path($$OUT_PWD)\"
    copyTarget.depends += copycontrollers
    QMAKE_EXTRA_TARGETS += copycontrollers

    win32:copystructural.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\StructuralFiles)\" \"$$shell_path($$OUT_PWD\\release\\StructuralFiles)\"
    unix:copystructural.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\StructuralFiles)\" \"$$shell_path($$OUT_PWD)\"
    copyTarget.depends += copystructural
    QMAKE_EXTRA_TARGETS += copystructural

    win32:copyprojects.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\CertTest)\" \"$$shell_path($$OUT_PWD\\release\\CertTest)\"
    unix:copyprojects.commands = $(COPY_DIR) \"$$shell_path($$PWD\\data\\CertTest)\" \"$$shell_path($$OUT_PWD)\"
    copyTarget.depends += copyprojects
    QMAKE_EXTRA_TARGETS += copyprojects
}
