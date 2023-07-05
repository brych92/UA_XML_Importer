
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QProcess, QProcessEnvironment
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import *

import xml.etree.ElementTree as ET
import sys
import os
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsProject

class Importer:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.isRun=None
        
    def initGui(self):
        icon = QIcon(os.path.join(self.plugin_dir,"icon.png"))
        action = QAction(icon, "UA XML Importer ( ◔ ౪◔)⊃━☆ﾟ.*・",self.iface.mainWindow())
        action.triggered.connect(self.run)
        action.setEnabled(True)
        self.iface.addToolBarIcon(action)
        self.actions.append(action)
    def unload(self):        
        for action in self.actions:
            self.iface.removeToolBarIcon(action)        
        
    def run(self): 
        # layer =  QgsVectorLayer('Polygon?crs=epsg:7827&field=File_name:string&field=File_name:string&', 'XML' , "memory")
        parcel_layer = QgsVectorLayer('Polygon?crs=epsg:7827&field=File_name:string&field=Purpose:string&field=Use:string&field=Ownership:string&field=Area:string', 'XML_parcel' , "memory")
        rest_layer =  QgsVectorLayer('Polygon?crs=epsg:7827&field=File_name:string&field=RestrictionCode:string&field=RestrictionName:string', 'XML_restrictions' , "memory")
        PLprov=parcel_layer.dataProvider()
        RLprov=rest_layer.dataProvider()
        # pr = layer.dataProvider()
        pathArr=[]
        pathArr=QFileDialog.getOpenFileNames(None,"Вкажіть шлях до XML (всі файли мають мати однакові СК!!!) ", os.path.expanduser('~'), "Кадастровий XML (*.xml)")[0]
        #print(pathArr)
        if pathArr!=[]:
            for path in pathArr:
                if path!='':
                    print('Обробляю '+os.path.basename(path))
                    
                    tree = ET.parse(path)
                    root = tree.getroot()
                   
                    points={}
                    for child in root.findall("./InfoPart/MetricInfo/PointInfo/Point"):
                        points[int(child.find("./UIDP").text)]=QgsPointXY(float(child.find("./Y").text),float(child.find("./X").text))
                    linesC={}
                    for child in root.findall("./InfoPart/MetricInfo/Polyline/PL"):
                        linesC[int(child.find("./ULID").text)]=[int(i.text) for i in child.findall("./Points/P")]
                    
                    lines={}
                    for linenum in linesC:
                        lines[linenum]=[points[linesC[linenum][0]],points[linesC[linenum][1]]]
#parcel---------------------------------------------- 
                    feature = QgsFeature()
                    parcel_info=root.find("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo")
                    feature.initAttributes(5)
                    feature.setAttribute(0,os.path.basename(path))
                    feature.setAttribute(2,parcel_info.find("./CategoryPurposeInfo/Purpose").text)
                    feature.setAttribute(1,parcel_info.find("./CategoryPurposeInfo/Use").text)
                    Ownership={"100":"Приватна власність","200":"Комунальна власність", "300":"Державна власність"}                    
                    feature.setAttribute(3,Ownership[parcel_info.find("./OwnershipInfo/Code").text])
                    feature.setAttribute(4,parcel_info.find("./ParcelMetricInfo/Area/Size").text+' '+parcel_info.find("./ParcelMetricInfo/Area/MeasurementUnit").text)
                    ParcExtBound=[] 
                    for child in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/ParcelMetricInfo/Externals/Boundary/Lines/Line"):
                        ParcExtBound=ParcExtBound+lines[int(child.find("./ULID").text)]
                    geom=QgsGeometry().fromPolygonXY([ParcExtBound])
                    
                    for child in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/ParcelMetricInfo/Externals/Internals/Boundary"):
                        ParcInttBound=[]
                        for shape in child.findall("./Lines/Line"):
                            ParcInttBound=ParcInttBound+lines[int(shape.find("./ULID").text)]
                        geom=geom.difference(QgsGeometry().fromPolygonXY([ParcInttBound]))
                    feature.setGeometry(geom)
                    #print(os.path.basename(path)+"\r\b"+str(geom))
                    PLprov.addFeature(feature)
#restrictions------------------------------------------------
                    
                    if root.find("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/Restrictions/RestrictionInfo/RestrictionCode")!=None:
                        for restriction in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/Restrictions/RestrictionInfo"):                            
                            feature = QgsFeature()
                            feature.initAttributes(3)
                            feature.setAttribute(0,os.path.basename(path))
                            
                            feature.setAttribute(1,restriction.find("./RestrictionCode").text)
                            feature.setAttribute(2,restriction.find("./RestrictionName").text)
                            ParcExtBound=[]                            
                            for child in restriction.findall("./Externals/Boundary/Lines/Line"):
                                ParcExtBound=ParcExtBound+lines[int(child.find("./ULID").text)]
                            geom=QgsGeometry().fromPolygonXY([ParcExtBound])                            
                            for child in restriction.findall("./Externals/Internals/Boundary"):                                
                                ParcInttBound=[]
                                for shape in child.findall("./Lines/Line"):
                                    ParcInttBound=ParcInttBound+lines[int(shape.find("./ULID").text)]
                                geom=geom.difference(QgsGeometry().fromPolygonXY([ParcInttBound]))
                            feature.setGeometry(geom)
                            #print(os.path.basename(path)+"\r\b"+str(geom))
                            RLprov.addFeature(feature)
            if PLprov.featureCount()!=0 or RLprov.featureCount()!=0:
                rest_layer.updateExtents()
                parcel_layer.updateExtents()
                QgsProject.instance().addMapLayers([rest_layer,parcel_layer])
                msgBox = QMessageBox()
                msgBox.setText('Створено тимчасовий шар "XML", будь ласка налаштуйте для нього відповідну ск.')
                msgBox.exec()
            else:
                msgBox = QMessageBox()
                msgBox.setText("Халепка, об'єкти не додані")
                msgBox.exec()

            
            


