#! python3  # noqa: E265

"""
/***************************************************************************
 GmlasPanelMixin
                                 A QGIS plugin
 GMLAS Plugin
                             -------------------
        begin                : 2016-12-09
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Arnaud Morvan - www.camptocamp.com
        email                : arnaud.morvan@camptocamp.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# PyQGIS
import processing
import subprocess
import shlex
# 3rd party
from osgeo import gdal
from qgis.core import Qgis, QgsApplication, QgsProcessingFeedback
from qgis.PyQt.QtCore import QEventLoop, Qt, pyqtSlot
from qgis.PyQt.QtWidgets import QFileDialog, QProgressDialog

# project package
from gml_application_schema_toolbox.__about__ import __title__
from gml_application_schema_toolbox.core.proxy import qgis_proxy_settings
from gml_application_schema_toolbox.toolbelt.log_handler import PlgLogger

# ############################################################################
# ########## Classes ###############
# ##################################


class GmlasPanelMixin:
    def __init__(self):
        # map to the plugin log handler
        self.plg_logger = PlgLogger()

    @pyqtSlot()
    def on_gmlasConfigButton_clicked(self):
        filepath, suffix_filter = QFileDialog.getOpenFileName(
            parent=self,
            caption=self.tr("Open GMLAS config file"),
            directory=self.gmlasConfigLineEdit.text(),
            filter=self.tr("XML Files (*.xml)"),
        )
        if filepath:
            self.gmlasConfigLineEdit.setText(filepath)

    def translate(self, params):
        if params is None:
            return
        params["callback"] = self.translate_callback

        dlg = QProgressDialog(self)
        dlg.setWindowTitle(__title__)
        dlg.setLabelText("Operation in progress")
        dlg.setMinimum(0)
        dlg.setMaximum(100)
        dlg.setWindowModality(Qt.WindowModal)
        self.progress_dlg = dlg

        self.setCursor(Qt.WaitCursor)
        try:
            self.plg_logger.log("gdal.VectorTranslate({})".format(str(params)))
            gdal.PushErrorHandler(self.plg_logger.gdal_error_handler)
            with qgis_proxy_settings():
                res = gdal.VectorTranslate(**params)
            gdal.PopErrorHandler()
            self.plg_logger.log(str(res))
        finally:
            self.unsetCursor()
            self.progress_dlg.reset()
            self.progress_dlg = None

    def translate_callback(self, pct, msg, user_data):
        self.progress_dlg.setValue(int(100 * pct))
        QgsApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        if self.progress_dlg.wasCanceled():
            return 0
        return 1

    def build_ogr2ogr_command(self,params, s_srs="epsg:2180", t_srs="epsg:2180"):
        """
        Generuje polecenie ogr2ogr jako listę argumentów subprocess
        na podstawie słownika params w stylu QGIS Processing.

        :param params: dict zawierający klucze INPUT, OUTPUT, OPTIONS
        :param s_srs: źródłowy układ współrzędnych (domyślnie EPSG:2180)
        :param t_srs: docelowy układ współrzędnych (domyślnie EPSG:2180)
        :return: lista argumentów subprocess dla ogr2ogr
        """

        input_gmlas = params.get('INPUT')
        output_pg = params.get('OUTPUT')

        # Oczyszczenie connection string z pojedynczych cudzysłowów, jeśli występują
        output_pg_clean = output_pg.replace("'", "") if output_pg else ""

        # Rozbicie options na listę
        options_str = params.get('OPTIONS', '')
        options_list = shlex.split(options_str)

        # Budowa komendy
        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            "-s_srs", s_srs,
            "-t_srs", t_srs,
            output_pg_clean,
            input_gmlas
        ]

        # Dodanie opcji na końcu
        cmd.extend(options_list)

        return cmd

    def translate_processing(self, params):
        """Use GDAL processing to convert GMLAS to database and vice versa.

        :param params: Parameters for GDAL processing
        :type params: dict
        """
        feedback = QgsProcessingFeedback()
        if Qgis.versionInt() < 32400:
            self.log(
                message=f"gmlas:convertformat_gmlas with params = {params}", log_level=4
            )
            res = processing.run("gmlas:convertformat_gmlas", params, feedback=feedback)
        else:
            self.log(message=f"gdal:convertformat with params = {params}", log_level=4)
            res = processing.run("gdal:convertformat", params, feedback=feedback)
        self.log(message=str(res), log_level=4)
        self.log(message=feedback.textLog(), log_level=4)

    def translate_processing_import(self, params):
        """Use GDAL processing to convert GMLAS to database and vice versa.

        :param params: Parameters for GDAL processing
        :type params: dict
        """
        feedback = QgsProcessingFeedback()
        if Qgis.versionInt() < 32400:
            self.log(
                message=f"gmlas:convertformat_gmlas with params = {params}", log_level=4
            )
            res = processing.run("gmlas:convertformat_gmlas", params, feedback=feedback)
        else:
            # zrezygnowanie z processing na rzecz subprosess z powodu dodawania pustego formatu
            # self.log(message=f"gdal:convertformat with params = {params}", log_level=4)
            # res = processing.run("gdal:convertformat", params, feedback=feedback)
            #
            cmd = self.build_ogr2ogr_command(params)
            self.log(message=f"Polecenie ogr2ogr = {cmd}", log_level=4)
            res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.log(message=str(res), log_level=4)
        self.log(message=feedback.textLog(), log_level=4)
