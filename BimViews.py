#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 Yorik van Havre <yorik@uncreated.net>              *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

"""This module contains FreeCAD commands for the BIM workbench"""

import os,FreeCAD,FreeCADGui,sys
from DraftTools import translate

def QT_TRANSLATE_NOOP(ctx,txt): return txt # dummy function for the QT translator

UPDATEINTERVAL = 2000 # number of milliseconds between BIM Views window update



class BIM_Views:


    def GetResources(self):

        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons","BIM_Views.svg"),
                'MenuText': QT_TRANSLATE_NOOP("BIM_Views", "Views manager"),
                'ToolTip' : QT_TRANSLATE_NOOP("BIM_Views", "Shows or hides the views manager"),
                'Accel': 'Ctrl+9'}

    def Activated(self):

        from PySide import QtCore,QtGui
        vm = findWidget()
        bimviewsbutton = None
        mw = FreeCADGui.getMainWindow()
        st = mw.statusBar()
        statuswidget = st.findChild(QtGui.QToolBar,"BIMStatusWidget")
        if statuswidget:
            if hasattr(statuswidget,"bimviewsbutton"):
                bimviewsbutton = statuswidget.bimviewsbutton
        if vm:
            if vm.isVisible():
                vm.hide()
                if bimviewsbutton:
                    bimviewsbutton.setChecked(False)
                    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/BIM").SetBool("RestoreBimViews",False)
            else:
                vm.show()
                if bimviewsbutton:
                    bimviewsbutton.setChecked(True)
                    FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/BIM").SetBool("RestoreBimViews",True)
                self.update()
        else:
            vm = QtGui.QDockWidget()

            # create the dialog
            dialog = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"dialogViews.ui"))
            vm.setWidget(dialog)
            vm.tree = dialog.tree

            # set button sizes
            size = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/General").GetInt("ToolbarIconSize",24)
            for button in [dialog.buttonAddLevel,
                           dialog.buttonAddProxy,
                           dialog.buttonDelete,
                           dialog.buttonToggle,
                           dialog.buttonIsolate,
                           dialog.buttonSaveView]:
                button.setMaximumSize(QtCore.QSize(size+4,size+4))
                button.setIconSize(QtCore.QSize(size,size))

            # set button icons
            import Arch_rc,Draft_rc
            dialog.buttonAddLevel.setIcon(QtGui.QIcon(":/icons/Arch_Floor.svg"))
            dialog.buttonAddProxy.setIcon(QtGui.QIcon(":/icons/Draft_SelectPlane.svg"))
            dialog.buttonDelete.setIcon(QtGui.QIcon(":/icons/delete.svg"))
            dialog.buttonToggle.setIcon(QtGui.QIcon(":/icons/dagViewVisible.svg"))
            dialog.buttonIsolate.setIcon(QtGui.QIcon(":/icons/view-refresh.svg"))
            dialog.buttonSaveView.setIcon(QtGui.QIcon(":/icons/view-perspective.svg"))

            # connect signals
            dialog.buttonAddLevel.clicked.connect(self.addLevel)
            dialog.buttonAddProxy.clicked.connect(self.addProxy)
            dialog.buttonDelete.clicked.connect(self.delete)
            dialog.buttonToggle.clicked.connect(self.toggle)
            dialog.buttonIsolate.clicked.connect(self.isolate)
            dialog.buttonSaveView.clicked.connect(self.saveView)
            dialog.tree.itemClicked.connect(self.select)
            dialog.tree.itemDoubleClicked.connect(show)

            # set the dock widget
            vm.setObjectName("BIM Views Manager")
            vm.setWindowTitle(translate("BIM","BIM Views manager"))
            mw = FreeCADGui.getMainWindow()
            mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, vm)

            # restore saved settings
            pref = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/BIM")
            vm.tree.setColumnWidth(0,pref.GetInt("ViewManagerColumnWidth",100))
            vm.setFloating(pref.GetFloat("ViewManagerFloating",False))

            # check the status bar button
            if bimviewsbutton:
                bimviewsbutton.setChecked(True)
            pref.SetBool("RestoreBimViews",True)

            self.update()

    def update(self,retrigger=True):

        "updates the view manager"

        from PySide import QtCore,QtGui
        vm = findWidget()
        if vm and FreeCAD.ActiveDocument:
            if vm.isVisible():
                vm.tree.clear()
                import Draft
                for obj in FreeCAD.ActiveDocument.Objects:
                    if obj and (Draft.getType(obj) in ["Building","BuildingPart","WorkingPlaneProxy"]):
                        it = QtGui.QTreeWidgetItem([obj.Label,FreeCAD.Units.Quantity(obj.Placement.Base.z,FreeCAD.Units.Length).UserString])
                        it.setToolTip(0,obj.Name)
                        if obj.ViewObject:
                            if hasattr(obj.ViewObject,"Proxy") and hasattr(obj.ViewObject.Proxy,"getIcon"):
                                it.setIcon(0,QtGui.QIcon(obj.ViewObject.Proxy.getIcon()))
                        vm.tree.addTopLevelItem(it)
        if retrigger:
            QtCore.QTimer.singleShot(UPDATEINTERVAL, self.update)
        
        # save state
        pref = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/BIM")
        pref.SetInt("ViewManagerColumnWidth",vm.tree.columnWidth(0))
        pref.SetFloat("ViewManagerFloating",vm.isFloating())

    def select(self,item,column=None):
        
        "selects a doc object corresponding to an item"
        
        name = item.toolTip(0)
        obj = FreeCAD.ActiveDocument.getObject(name)
        if obj:
            FreeCADGui.Selection.clearSelection()
            FreeCADGui.Selection.addSelection(obj)

    def addLevel(self):
        
        "adds a building part"

        import Arch
        FreeCAD.ActiveDocument.openTransaction("Create BuildingPart")
        Arch.makeFloor()
        FreeCAD.ActiveDocument.commitTransaction()
        FreeCAD.ActiveDocument.recompute()
        self.update(False)

    def addProxy(self):

        "adds a WP proxy"

        import Draft
        FreeCAD.ActiveDocument.openTransaction("Create WP Proxy")
        Draft.makeWorkingPlaneProxy(FreeCAD.DraftWorkingPlane.getPlacement())
        FreeCAD.ActiveDocument.commitTransaction()
        FreeCAD.ActiveDocument.recompute()
        self.update(False)

    def delete(self):
        
        "deletes the selected object"

        vm = findWidget()
        if vm:
            if vm.tree.selectedItems():
                FreeCAD.ActiveDocument.openTransaction("Delete")
                for item in vm.tree.selectedItems():
                    obj = FreeCAD.ActiveDocument.getObject(item.toolTip(0))
                    if obj:
                        FreeCAD.ActiveDocument.removeObject(obj.Name)
                FreeCAD.ActiveDocument.commitTransaction()
                FreeCAD.ActiveDocument.recompute()
                self.update(False)

    def toggle(self):

        "toggle selected item on/off"

        vm = findWidget()
        if vm:
            for item in vm.tree.selectedItems():
                obj = FreeCAD.ActiveDocument.getObject(item.toolTip(0))
                if obj:
                    obj.ViewObject.Visibility = not(obj.ViewObject.Visibility)
            FreeCAD.ActiveDocument.recompute()

    def isolate(self):

        "turns all items off except the selected ones"
        
        vm = findWidget()
        if vm:
            onnames = [item.toolTip(0) for item in vm.tree.selectedItems()]
            for i in range(vm.tree.topLevelItemCount()):
                item = vm.tree.topLevelItem(i)
                if item.toolTip(0) not in onnames:
                    obj = FreeCAD.ActiveDocument.getObject(item.toolTip(0))
                    if obj:
                        obj.ViewObject.Visibility = False
            FreeCAD.ActiveDocument.recompute()

    def saveView(self):

        "save the current camera angle to the selected item"

        vm = findWidget()
        if vm:
            for item in vm.tree.selectedItems():
                obj = FreeCAD.ActiveDocument.getObject(item.toolTip(0))
                if obj:
                    if hasattr(obj.ViewObject.Proxy,"writeCamera"):
                        obj.ViewObject.Proxy.writeCamera()
        FreeCAD.ActiveDocument.recompute()




FreeCADGui.addCommand('BIM_Views',BIM_Views())



# These functions need to be localized outside the command class, as they are used outside this module



def findWidget():

    "finds the manager widget, if present"

    from PySide import QtGui
    mw = FreeCADGui.getMainWindow()
    vm = mw.findChild(QtGui.QDockWidget,"BIM Views Manager")
    if vm:
        return vm
    return None



def show(item,column=None):

    "item has been double-clicked"

    vm = findWidget()
    if isinstance(item,str) or ((sys.version_info.major < 3) and isinstance(item,unicode)):
        obj = FreeCAD.ActiveDocument.getObject(item)
    else:
        if column == 1:
            # user clicked the level field
            if vm:
                vm.tree.editItem(item,column)
                return
        obj = FreeCAD.ActiveDocument.getObject(item.toolTip(0))
    if obj:
        FreeCADGui.Selection.clearSelection()
        FreeCADGui.Selection.addSelection(obj)
        FreeCADGui.runCommand("Draft_SelectPlane")
    if vm:
        # store the last double-clicked item for the BIM WPView command
        if isinstance(item,str) or ((sys.version_info.major < 3) and isinstance(item,unicode)):
            vm.lastSelected = item
        else:
            vm.lastSelected = item.toolTip(0)
