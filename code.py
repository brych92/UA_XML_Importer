
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
        err_arr=[] #list for parcels with errors during import
        finished_arr=[] #list of all files
        err_dict={'parc_inv':[],'rest_inv':[],'parc_err':[],'rest_err':[]}
        def get_crs(root):            
            epsg={
                'SC63X/1':'7825',
                'SC63X/2':'7826',
                'SC63X/3':'7827',
                'SC63X/4':'7828',
                'SC63X/5':'7829',
                'SC63X/6':'7830',
                'SC63X/7':'7831',
                'Local/01': '9831',
                'Local/05': '9832',
                'Local/07': '9833',
                'Local/12': '9834',
                'Local/14': '9835',
                'Local/18': '9836',
                'Local/21': '9837',
                'Local/23': '9838',
                'Local/35': '9840',
                'Local/44': '9841',
                'Local/46': '9851',
                'Local/48': '9852',
                'Local/51': '9853',
                'Local/53': '9854',
                'Local/56': '9855',
                'Local/59': '9856',
                'Local/61': '9857',
                'Local/63': '9858',
                'Local/65': '9859',
                'Local/68': '9860',
                'Local/71': '9861',
                'Local/73': '9862',
                'Local/74': '9863',
                'Local/85': '9865',
                'Local/32': '9821',
                'Local/26': '9839',
                'Local/80': '9864',
                'UCS-2000/7':'6381',
                'UCS-2000/8':'6382',
                'UCS-2000/9':'6383',
                'UCS-2000/10':'6384',
                'UCS-2000/11':'6385',
                'UCS-2000/12':'6386',
                'UCS-2000/13':'6387',
            }
            crs_type=root.find("./InfoPart/MetricInfo/CoordinateSystem/").tag
            if crs_type=="SC63":
                crs_type=crs_type+root.find("./InfoPart/MetricInfo/CoordinateSystem/*/").tag
                crs_zone=root.find("./InfoPart/MetricInfo/PointInfo/Point/Y").text[0]
                crs_comb=crs_type+'/'+crs_zone
            elif crs_type=="USC2000":
                crs_zone=root.find("./InfoPart/MetricInfo/PointInfo/Point/Y").text[0]
                crs_comb=crs_type+'/'+crs_zone
            elif crs_type=="Local":
                crs_zone=root.find("./InfoPart/MetricInfo/CoordinateSystem/").text[-2:]
                crs_comb='Local/'+crs_zone
            else:
                crs_comb=root.find("./InfoPart/MetricInfo/CoordinateSystem/").tag
            if crs_comb in epsg:
                # print(epsg[crs_comb])
                return ['crs=epsg:'+epsg[crs_comb]+'&',crs_comb]
            else:
                # print("Ск не розпізнана")
                return ['',crs_comb]
        def get_geometry(xml_path):#шлях до /externals
            if xml_path==None: return None
            ParcExtBound=[]            
            for child in xml_path.findall("./Boundary/Lines/Line"):
                ParcExtBound=ParcExtBound+lines[int(child.find("./ULID").text)]
            geom=QgsGeometry().fromPolygonXY([ParcExtBound])                    
            for child in xml_path.findall("./Internals/Boundary"):
                ParcInttBound=[]
                for shape in child.findall("./Lines/Line"):
                    ParcInttBound=ParcInttBound+lines[int(shape.find("./ULID").text)]
                geom=geom.difference(QgsGeometry().fromPolygonXY([ParcInttBound]))
            return geom
        pathArr=[]
        pathArr=QFileDialog.getOpenFileNames(None,"Вкажіть шлях до XML (всі файли мають мати однакові СК!!!) ", os.path.expanduser('~'), "Кадастровий XML (*.xml)")[0]
        if pathArr==[]:
            print('Нічого не вибрано!')
            return
        print(str(len(pathArr))+' файлів до обробки:')
        print('\t'+str(pathArr))
        crs_parc_layers={}
        crs_rest_layers={}        
        crs_layers={}
        for path in pathArr:
            if path!='':
                print('Обробляю '+os.path.basename(path))
                _print=lambda t: print('\t'+str(t))
                tree = ET.parse(path)
                root = tree.getroot()
                crs=get_crs(root)[0]                
                _print('З тегу СК прочитано:'+get_crs(root)[1])
                if crs: _print(crs)
                if crs=='': crs=get_crs(root)[1] #якшо не визначило epsg тоді вписуємо шо воно витягло з XML
                points={}#словарь з списком точок 'UIDP': [x,y]
                for child in root.findall("./InfoPart/MetricInfo/PointInfo/Point"):
                    points[int(child.find("./UIDP").text)]=QgsPointXY(float(child.find("./Y").text),float(child.find("./X").text))
                _print(f"Знайдено {len(points)} точок")
                linesC={}#словарь з списком ліній 'ULID':[UIDP, UIDP, UIDP...]
                for child in root.findall("./InfoPart/MetricInfo/Polyline/PL"):
                    linesC[int(child.find("./ULID").text)]=[int(i.text) for i in child.findall("./Points/P")]
                _print(f"Знайдено {len(linesC)} ліній")
                lines={}#словарь з списком ліній 'ULID':[QgsPointXY, QgsPointXY, QgsPointXY...]
                for linenum in linesC:
                    lines[linenum]=[points[i] for i in linesC[linenum]]

#parcel---------------------------------------------- 
                feature = QgsFeature()
                _print('Починаю зчитувати атрибути')
                parcel_info=root.find("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo")
                if parcel_info:
                    _print('\t'+str(parcel_info))
                    feature.initAttributes(5)
                    feature.setAttribute(0,os.path.basename(path))
                    feature.setAttribute(2,parcel_info.find("./CategoryPurposeInfo/Purpose").text)   
                    feature.setAttribute(1,parcel_info.find("./CategoryPurposeInfo/Use").text)                    
                    try:feature.setAttribute(3,{"100":"Приватна власність","200":"Комунальна власність", "300":"Державна власність"}[parcel_info.find("./OwnershipInfo/Code").text])
                    except KeyError: _print("\tOwnership не знайдено")
                    feature.setAttribute(4,parcel_info.find("./ParcelMetricInfo/Area/Size").text+' '+parcel_info.find("./ParcelMetricInfo/Area/MeasurementUnit").text)
                
                geom=get_geometry(root.find("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/ParcelMetricInfo/Externals"))  
                if geom:
                    if geom.isGeosValid():
                        _print('Геометрія ділянки пройшла валідацію.')
                    else:
                        if not os.path.basename(path) in err_dict['parc_inv']: err_dict['parc_inv'].append(os.path.basename(path))
                        _print('Геометрія ділянки не пройшла валідацію, перевірьте правильність імпортованої геометрії.')
                        _print('\tGeom:')
                        _print('\t\t'+str(geom))
                    feature.setGeometry(geom)
                    if not crs in crs_layers: crs_layers[crs]={}
                    if not 'Parcels' in crs_layers[crs]: crs_layers[crs]['Parcels']=[]
                    crs_layers[crs]['Parcels'].append(feature)
                    if not os.path.basename(path)in finished_arr: finished_arr.append(os.path.basename(path))
                else:
                    if not os.path.basename(path) in err_dict['parc_err']: err_dict['parc_err'].append(os.path.basename(path))
                    _print('Не можу знайти геометрію ділянки. Ділянка не буде додана.')      
#restrictions------------------------------------------------
                _print('Перевіряю обмеження...')
                for restriction in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/Restrictions/RestrictionInfo"): 
                    _print(f"Розглядаємо обмеження {restriction.find('./RestrictionCode').text} {restriction.find('./RestrictionName').text}...")
                    feature = QgsFeature()
                    feature.initAttributes(3)
                    feature.setAttribute(0,os.path.basename(path))
                    feature.setAttribute(1,restriction.find("./RestrictionCode").text)
                    feature.setAttribute(2,restriction.find("./RestrictionName").text)
                    geom=get_geometry(restriction.find("./Externals"))
                    if geom:
                        if geom.isGeosValid():
                            _print('Геометрія Обмеження пройшла валідацію.')
                        else:
                            if not os.path.basename(path) in err_dict['rest_inv']: err_dict['rest_inv'].append(os.path.basename(path))
                            _print('Геометрія Обмеження не пройшла валідацію, перевірьте правильність імпортованої геометрії.')
                            _print('\tGeom:')
                            _print('\t\t'+str(geom))
                        feature.setGeometry(geom)
                        if not crs in crs_layers: crs_layers[crs]={}
                        if not 'Restrictions' in crs_layers[crs]: crs_layers[crs]['Restrictions']=[]
                        crs_layers[crs]['Restrictions'].append(feature)
                        if not os.path.basename(path)in finished_arr: finished_arr.append(os.path.basename(path))
                    else:
                        if not os.path.basename(path) in err_dict['rest_err']: err_dict['rest_err'].append(os.path.basename(path))
                        _print('Не можу знайти геометрію обмеження. Обмеження не буде додано.')
                
        for crs in crs_layers:
            if crs[0:4]=='crs=':
                epsg=crs                
                group = QgsProject.instance().layerTreeRoot().insertGroup(0,crs[4:-1])
                print(f'\tСтворюю групу шарів {crs[4:-1]}.')
            else:
                epsg=''
                group = QgsProject.instance().layerTreeRoot().insertGroup(0,crs)
                print(f'\tСтворюю групу шарів {crs}.')
            if 'Restrictions' in crs_layers[crs]:
                layer = QgsVectorLayer(f'Polygon?{epsg}field=File_name:string&field=RestrictionCode:string&field=RestrictionName:string', 'XML_restrictions' , "memory")
                for feature in crs_layers[crs]['Restrictions']:
                    layer.dataProvider().addFeature(feature)
                if layer.featureCount()!=0:
                    layer.updateExtents()
                    QgsProject.instance().addMapLayer(layer, False)
                    group.addLayer(layer)
                    print('\t\tСтворюю шар з обмеженнями в групі.')
            else:
                print("\t\tОб'єкти обмежень відсутні.")
            
            if 'Parcels' in crs_layers[crs]:
                layer = QgsVectorLayer(f'Polygon?{epsg}field=File_name:string&field=Purpose:string&field=Use:string&field=Ownership:string&field=Area:string', 'XML_parcel' , "memory")
                for feature in crs_layers[crs]['Parcels']:
                    layer.dataProvider().addFeature(feature)
                if layer.featureCount()!=0:
                    layer.updateExtents()
                    QgsProject.instance().addMapLayer(layer, False)
                    group.addLayer(layer)
                    print('\t\tСтворюю шар з ділянками в групі.')
            else:
                print("\t\tОб'єкти обмежень відсутні.")
            layer=None

        if len(finished_arr)>0:
            msgBox = QMessageBox()
            if len(err_dict["parc_err"])>0:
                parc_err=f'\r\n\r\nЗемельні ділянки з наступних файлів не були завантажені: \r\n{err_dict["parc_err"]}.'
            else:
                parc_err=''
            if len(err_dict["rest_err"])>0:
                rest_err=f'\r\n\r\nОбмеження ділянки з наступних файлів не були завантажені: \r\n{err_dict["rest_err"]}.'
            else:
                rest_err=''
            if len(err_dict["parc_inv"])>0:
                parc_inv=f'\r\n\r\nОбмеження ділянки з наступних файлів мають не валідну геометрію: \r\n {err_dict["parc_inv"]}.'
            else:
                parc_inv=''
            if len(err_dict["rest_inv"])>0:
                rest_inv=f'\r\n\r\nОбмеження ділянки з наступних файлів мають не валідну геометрію: \r\n {err_dict["rest_inv"]}.'
            else:
                rest_inv=''
            if len(parc_err+rest_err+parc_inv+rest_inv)==0:
                parc_err='\r\n\r\nВсі файли були імпортовані без помилок. Але все рівно все перевірьте!!!' 
                
            msgBox.setText(f'Оброблено {len(pathArr)} файлів.{parc_err}{rest_err}{parc_inv}{rest_inv}\r\n\r\nСтворено тимчасові шари під різні кординати, будь ласка перевірьте відповідність СК!')
            msgBox.exec()
            msgBox.setText('Серйозно, плагін тестовий, перевіряйте імпорт, і давайте фідбек!!!')
            msgBox.exec()
            msgBox.setText("(ง •̀_•́)ง")
            msgBox.exec()
        else:
            msgBox = QMessageBox()
            msgBox.setText("Халепка, ні одного об'єкта не додано")
            msgBox.exec()

        
        


