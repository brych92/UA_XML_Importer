
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QProcess, QProcessEnvironment
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import *


import random
import threading

import xml.etree.ElementTree as ET
import sys
import os
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsApplication, QgsRectangle, QgsCoordinateTransform

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
    def zoom_to_layers(self,layers):
        canvas = self.iface.mapCanvas()
        extent = QgsRectangle()
        transform_context = QgsProject.instance().transformContext()

        for layer in layers:
            if layer.crs() != canvas.mapSettings().destinationCrs():
                transform = QgsCoordinateTransform(layer.crs(), canvas.mapSettings().destinationCrs(), QgsProject.instance())
                bottom_left = QgsPointXY(layer.extent().xMinimum(), layer.extent().yMinimum())
                top_right = QgsPointXY(layer.extent().xMaximum(), layer.extent().yMaximum())
                transformed_bottom_left = transform.transform(bottom_left)
                transformed_top_right = transform.transform(top_right)
                layer_extent = QgsRectangle(transformed_bottom_left, transformed_top_right)
            else:
                layer_extent = layer.extent()

            extent.combineExtentWith(layer_extent)

        canvas.setExtent(extent)
        canvas.refresh()
    def run(self):
        finished_arr=[]
        err_dict={'parc_inv':[],'rest_inv':[],'other_inv':[],'parc_err':[],'rest_err':[],'other_err':[]}
        crs_layers={}
        pathArr=[]
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
            crs_type=root.find("./InfoPart/MetricInfo/CoordinateSystem/")            
            if crs_type!=None:
                crs_type=crs_type.tag
            else:
                return ['','None']
            
            if crs_type=="SC63":
                crs_type=crs_type+root.find("./InfoPart/MetricInfo/CoordinateSystem/*/").tag
                crs_zone=root.find("./InfoPart/MetricInfo/PointInfo/Point/Y").text[0]
                crs_comb=crs_type+'/'+crs_zone
            elif crs_type=="USC2000":
                crs_zone=root.find("./InfoPart/MetricInfo/PointInfo/Point/Y").text[0]
                crs_comb=crs_type+'/'+crs_zone
            elif crs_type=="Local":
                try:
                    crs_zone=root.find("./InfoPart/MetricInfo/CoordinateSystem/").text[-2:]
                except AttributeError:
                    crs_zone='custom'
                crs_comb='Local/'+crs_zone
            else:
                crs_comb=root.find("./InfoPart/MetricInfo/CoordinateSystem/").tag
            if crs_comb in epsg:
                # print(epsg[crs_comb])
                return ['crs=epsg:'+epsg[crs_comb]+'&',crs_comb]
            else:
                # print("Ск не розпізнана")
                return ['',crs_comb]
        def get_geometry(xml_path):#об'єкт xmlPath до /externals
            if xml_path==None: return None
            res_geom= QgsGeometry.fromWkt('GEOMETRYCOLLECTION()')
            geom_arr=[]
            for element in xml_path:
                ParcExtBound=[]            
                for child in element.findall("./Boundary/Lines/Line"):                    
                    fp=child.find('./FP')
                    tp=child.find('./TP')
                    if fp!=None: fp=int(fp.text)
                    if tp!=None: tp=int(tp.text)
                    if fp in points and tp in points:
                        ParcExtBound=ParcExtBound+[points[fp],points[tp]]
                    else:
                        ParcExtBound=ParcExtBound+lines[int(child.find("./ULID").text)]                
                geom=QgsGeometry().fromPolygonXY([ParcExtBound]) 
                
                for child in element.findall("./Internals/Boundary"):
                    ParcInttBound=[]
                    for shape in child.findall("./Lines/Line"):
                        fp=shape.find('./FP')                    
                        tp=shape.find('./TP')                    
                        if fp!=None: fp=int(fp.text)
                        if tp!=None: tp=int(tp.text)
                        if fp in points and tp in points:
                            ParcInttBound=ParcInttBound+[points[fp],points[tp]]
                        else:
                            ParcInttBound=ParcInttBound+lines[int(shape.find("./ULID").text)]
                    geom=geom.difference(QgsGeometry().fromPolygonXY([ParcInttBound]))
                    geom_arr.append(geom)
                res_geom=res_geom.combine(geom.makeValid())   
            return res_geom
    
        pathArr=QFileDialog.getOpenFileNames(None,"Виберіть XML файл(файли) для імпорту", os.path.expanduser('~'), "Кадастровий XML (*.xml)")[0]
        if pathArr==[]:
            print('Нічого не вибрано!')
            return
        print(str(len(pathArr))+' файлів до обробки:')
        print('\t'+str(pathArr))
        
        window = QProgressDialog(self.iface.mainWindow())
        window.setWindowTitle("Обробляю...")            
        bar = QProgressBar(window)
        bar.setTextVisible(True)
        bar.setValue(0)
        bar.setMaximum(len(pathArr))
        window.setBar(bar)
        window.setMinimumWidth(300)
        window.show()
        

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

#Ділянки------------------------------------------------
                _print('Перевіряю ділянки...')
                for element in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo"):                    
                    try:
                        purpose=element.find("./CategoryPurposeInfo/Purpose").text
                    except AttributeError:
                        purpose='*не роспізнано*'
                        _print("\t\tPurpose не знайдено")
                    try:
                        use=element.find("./CategoryPurposeInfo/Use").text
                    except AttributeError:
                        use='*не роспізнано*'
                        _print("\t\tUse не знайдено")
                    try:
                        area=element.find("./ParcelMetricInfo/Area/Size").text
                    except AttributeError:
                        area='*не роспізнано*'
                        _print("\t\tПлощу не знайдено")
                    try:
                        area_unit=element.find("./ParcelMetricInfo/Area/MeasurementUnit").text
                    except AttributeError:
                        area_unit='?'
                        _print("\t\tОдиниці площі не знайдено")
                    feature = QgsFeature()
                    feature.initAttributes(5)
                    feature.setAttribute(0,os.path.basename(path))                    
                    feature.setAttribute(1,use) 
                    feature.setAttribute(2,purpose)                    
                    try:
                        feature.setAttribute(3,{"100":"Приватна власність","200":"Комунальна власність", "300":"Державна власність"}[element.find("./OwnershipInfo/Code").text])
                    except (KeyError, AttributeError):
                        feature.setAttribute(3,'*не роспізнано*')
                        _print("\t\tOwnership не знайдено")
                    feature.setAttribute(4,area+' '+area_unit)
                    
                    geom=get_geometry(element.findall("./ParcelMetricInfo/Externals"))
                    if geom:
                        if geom.isGeosValid():
                            _print('Геометрія ділянки пройшла валідацію.')
                        else:
                            if not os.path.basename(path) in err_dict['parc_inv']: err_dict['parc_inv'].append(os.path.basename(path))
                            _print('Геометрія ділянки не пройшла валідацію, перевірьте правильність імпортованої геометрії.')                        
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
                    try:
                        rest_code=restriction.find('./RestrictionCode').text
                    except AttributeError:
                        rest_code='*код не роспізнано*'                        
                    try:
                        rest_name=restriction.find('./RestrictionName').text
                    except AttributeError:
                        rest_name='*назву не роспізнано*'                        
                    _print(f"\tРозглядаємо обмеження {rest_code} {rest_name}...")
                    feature = QgsFeature()
                    feature.initAttributes(3)
                    feature.setAttribute(0,os.path.basename(path))
                    feature.setAttribute(1,rest_code)
                    feature.setAttribute(2,rest_name)
                    geom=get_geometry(restriction.findall("./Externals"))
                    if geom:
                        if geom.isGeosValid():
                            _print('\t\tГеометрія Обмеження пройшла валідацію.')
                        else:
                            if not os.path.basename(path) in err_dict['rest_inv']: err_dict['rest_inv'].append(os.path.basename(path))
                            _print('\t\tГеометрія Обмеження не пройшла валідацію, перевірьте правильність імпортованої геометрії.')                            
                        feature.setGeometry(geom)
                        if not crs in crs_layers: crs_layers[crs]={}
                        if not 'Restrictions' in crs_layers[crs]: crs_layers[crs]['Restrictions']=[]
                        crs_layers[crs]['Restrictions'].append(feature)
                        if not os.path.basename(path)in finished_arr: finished_arr.append(os.path.basename(path))
                    else:
                        if not os.path.basename(path) in err_dict['rest_err']: err_dict['rest_err'].append(os.path.basename(path))
                        _print('\t\tНе можу знайти геометрію обмеження. Обмеження не буде додано.')
#угіддя------------------------------------------------
                _print('Перевіряю угіддя...')
                for part in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/LandsParcel/LandParcelInfo"): 
                    try:
                        code=part.find('./LandCode').text
                    except AttributeError:
                        code='*код не роспізнано*'                        
                    try:
                        size=part.find('./MetricInfo/Area/Size').text
                    except AttributeError:
                        rest_name='*площу не визначено*'                        
                    try:
                        size=size+' '+part.find('./MetricInfo/Area/MeasurementUnit').text
                    except AttributeError:
                        size=size+' ?'
                    _print(f"\tРозглядаємо угіддя {code}...")
                    
                    feature = QgsFeature()
                    feature.initAttributes(3)
                    feature.setAttribute(0,os.path.basename(path))
                    feature.setAttribute(1,"Угіддя")
                    feature.setAttribute(2,code+"; "+size)
                    geom=get_geometry(part.findall("./MetricInfo/Externals"))
                    if geom:
                        if geom.isGeosValid():
                            _print('\t\tГеометрія угіддя пройшла валідацію.')
                        else:
                            if not os.path.basename(path) in err_dict['other_inv']: err_dict['other_inv'].append(os.path.basename(path))
                            _print('\t\tГеометрія угіддя не пройшла валідацію, перевірьте правильність імпортованої геометрії.')                            
                        feature.setGeometry(geom)
                        if not crs in crs_layers: crs_layers[crs]={}
                        if not 'Others' in crs_layers[crs]: crs_layers[crs]['Others']=[]
                        crs_layers[crs]['Others'].append(feature)
                        if not os.path.basename(path)in finished_arr: finished_arr.append(os.path.basename(path))
                    else:
                        if not os.path.basename(path) in err_dict['other_err']: err_dict['other_err'].append(os.path.basename(path))
                        _print('\t\tНе можу знайти геометрію Угіддя. Угіддя не буде додано.')

#Тер зони------------------------------------------------
                ter_zones={
                        '001':	'Межі адміністративно-територіальних утворень',
                        '002':	'Зони розподілу земель за їх основним цільовим призначенням',
                        '003':	'Економіко-планувальні зони',
                        '004':	'Зони агровиробничих груп ґрунтів ',
                        '005':	'Зони дії земельних сервітутів',
                        '006':	'Зони дії обмежень використання земель',
                        '007':	'Зони регулювання забудови (функціональні зони)',
                        '008':	'Зони санітарної охорони',
                        '009':	'Охоронні зони',
                        '010':	'Зони особливого режиму використання земель',
                        '011':	'Водоохоронні зони',
                        '012':	'Прибережні захисні смуги',
                        '013':	'Природно-сільськогосподарські зони',
                        '014':	'Еколого-економічні зони',
                        '015':	'Зони протиерозійного районування (зонування)',
                        '016':	'Ключові території екомережі',
                        '017':	'Сполучні території екомережі',
                        '018':	'Буферні зони екомережі',
                        '019':	'Відновлювані території екомережі',
                        '020':	'Інші територіальні зони'
                }
                _print('Перевіряю територіальні зони...')
                for part in root.findall("./InfoPart/TerritorialZoneInfo"): 
                    attr=''
                    try:
                        attr=attr+'Назва: '+part.find('./TerritorialZoneName').text+'; '
                    except AttributeError:
                        pass
                    try:
                        attr=attr+'Тип: '+ter_zones[part.find('./TerritorialZoneNumber/TerritorialZoneCode').text]+'; '
                    except AttributeError:
                        pass
                    try:
                        attr=attr+'Код: '+part.find('./TerritorialZoneNumber/TerritorialZoneShortNumber').text+'; '
                    except AttributeError:
                        pass 
                    feature = QgsFeature()
                    feature.initAttributes(3)
                    feature.setAttribute(0,os.path.basename(path))
                    feature.setAttribute(1,"Територіальна зона")
                    feature.setAttribute(2,attr)
                    geom=get_geometry(part.findall("./Externals"))
                    if geom:
                        if geom.isGeosValid():
                            _print('\t\tГеометрія тер. зони пройшла валідацію.')
                        else:
                            if not os.path.basename(path) in err_dict['other_inv']: err_dict['other_inv'].append(os.path.basename(path))
                            _print('\t\tГеометрія тер. зони не пройшла валідацію, перевірьте правильність імпортованої геометрії.')                            
                        feature.setGeometry(geom)
                        if not crs in crs_layers: crs_layers[crs]={}
                        if not 'Others' in crs_layers[crs]: crs_layers[crs]['Others']=[]
                        crs_layers[crs]['Others'].append(feature)
                        if not os.path.basename(path)in finished_arr: finished_arr.append(os.path.basename(path))
                    else:
                        if not os.path.basename(path) in err_dict['other_err']: err_dict['other_err'].append(os.path.basename(path))
                        _print('\t\tНе можу знайти геометрію тер. зони. Тер. зона не буде додано.')
            bar.setValue(bar.value()+1)

    
#Додавання об'єктів в шари               
        layers_arr=[]
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
                    layer.loadNamedStyle(os.path.join(os.path.dirname(__file__),"Styles\\restrictions.qml"))
                    layer.triggerRepaint()
                    QgsProject.instance().addMapLayer(layer, False)
                    group.addLayer(layer)
                    layers_arr.append(layer)
                    print('\t\tСтворюю шар з обмеженнями в групі.')
            else:
                print("\t\tОб'єкти обмежень відсутні.")

            if 'Others' in crs_layers[crs]:
                layer = QgsVectorLayer(f'Polygon?{epsg}field=File_name:string&field=Layer:string&field=Description:string', 'XML_others' , "memory")
                for feature in crs_layers[crs]['Others']:
                    layer.dataProvider().addFeature(feature)
                if layer.featureCount()!=0:
                    layer.updateExtents()
                    layer.loadNamedStyle(os.path.join(os.path.dirname(__file__),"Styles\\others.qml"))
                    layer.triggerRepaint()
                    QgsProject.instance().addMapLayer(layer, False)
                    group.addLayer(layer)
                    layers_arr.append(layer)
                    print('\t\tСтворюю шар з іншою геометрією в групі.')
            else:
                print("\t\tІнші об'єкти відсутні.")
            layer=None


            if 'Parcels' in crs_layers[crs]:
                layer = QgsVectorLayer(f'Polygon?{epsg}field=File_name:string&field=Purpose:string&field=Use:string&field=Ownership:string&field=Area:string', 'XML_parcels' , "memory")
                for feature in crs_layers[crs]['Parcels']:
                    layer.dataProvider().addFeature(feature)
                if layer.featureCount()!=0:
                    layer.updateExtents()
                    layer.loadNamedStyle(os.path.join(os.path.dirname(__file__),"Styles\\parcels.qml"))
                    layer.triggerRepaint()
                    QgsProject.instance().addMapLayer(layer, False)
                    group.addLayer(layer)
                    layers_arr.append(layer)
                    print('\t\tСтворюю шар з ділянками в групі.')
            else:
                print("\t\tОб'єкти земельних ділянок  відсутні.")
            layer=None

        window.close()
        if len(layers_arr)>0: self.zoom_to_layers(layers_arr)        
           
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
                parc_inv=f'\r\n\r\nЗемельні ділянки з наступних файлів мають не валідну геометрію: \r\n {err_dict["parc_inv"]}.'
            else:
                parc_inv=''
            if len(err_dict["rest_inv"])>0:
                rest_inv=f'\r\n\r\nОбмеження ділянки з наступних файлів мають не валідну геометрію: \r\n {err_dict["rest_inv"]}.'
            else:
                rest_inv=''
            if len(err_dict["parc_err"]+err_dict["rest_err"]+err_dict["parc_inv"]+err_dict["rest_inv"]+err_dict['other_err']+err_dict['other_inv'])==0:
                parc_err='\r\n\r\nВсі файли були імпортовані без помилок. Але все рівно все перевірьте!!!' 
                
            msgBox.setText(f'Оброблено {len(pathArr)} файлів.{parc_err}{rest_err}{parc_inv}{rest_inv}\r\n\r\nСтворено тимчасові шари під різні кординати, будь ласка перевірьте відповідність СК!')
            msgBox.exec()
            msgBox.setText('Плагін тестовий, перевіряйте імпорт, і давайте фідбек в чаті "JD help chat"!!!')
            msgBox.exec()
            smile={
                1:'⊂(◉‿◉)つ',
                2:'ʕ·͡ᴥ·ʔ',
                3:'ʕっ•ᴥ•ʔっ',
                4:'( ͡° ᴥ ͡°)',
                5:'( ✜︵✜ )',
                6:'(◕ᴥ◕ʋ)',
                7:'ᕕ(╭ರ╭ ͟ʖ╮•́)⊃¤=(————-',
                8:'(ﾉ◕ヮ◕)ﾉ*:・ﾟ✧',
                9:'／人◕ ‿‿ ◕人＼',
                10:' ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°)',
                11:'	¯\_( ͡° ͜ʖ ͡°)_/¯',
                12:'ʕ♥ᴥ♥ʔ'
            }
            rnd=random.randint(1,500)
            if rnd in smile:
                msgBox.setText("Посміхніться, сьогодні ваш день!\r\n\r\n"+smile[rnd])
                msgBox.exec()
        else:
            msgBox = QMessageBox()
            msgBox.setText("Халепка, ні одного об'єкта не додано")
            msgBox.exec()

        


