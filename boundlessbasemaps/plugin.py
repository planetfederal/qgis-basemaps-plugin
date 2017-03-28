# -*- coding: utf-8 -*-

"""
***************************************************************************
    __init__.py
    ---------------------
    Date                 : March 2017
    Copyright            : (C) 2017 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Alessandro Pasotti'
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

import os
import webbrowser

from qgis.PyQt.QtWidgets import QAction, QDialog
from qgis.PyQt.QtCore import QCoreApplication

from qgis.core import QgsApplication
from qgis.gui import QgsMessageBar

from qgiscommons.settings import addSettingsMenu, removeSettingsMenu, readSettings, pluginSetting, setPluginSetting
from qgiscommons.gui import addAboutMenu, removeAboutMenu

from boundlessbasemaps import utils


PROJECT_DEFAULT_TEMPLATE = os.path.join(os.path.dirname(__file__), 'project_default.qgs.tpl')


class BasemapsConfigError(Exception):
    """Config step gone wrong"""
    pass


class Basemaps:
    def __init__(self, iface):
        self.iface = iface
        try:
            from .tests import testerplugin
            from qgistester.tests import addTestModule
            addTestModule(testerplugin, "boundlessbasemaps")
        except:
            pass

        try:
            from lessons import addLessonsFolder
            folder = os.path.join(os.path.dirname(__file__), "_lessons")
            addLessonsFolder(folder)
        except:
            pass
        readSettings()
        if not pluginSetting('first_time_setup_done'):
            self.iface.initializationCompleted.connect(self.setup)

    def tr(self, msg):
        return QCoreApplication.translate('boundlessbasemaps', msg)

    def setup(self, username=None, password=None):
        """Configuration wizard"""
        from gui.setupwizard import SetupWizard
        settings = {
            "maps_uri": pluginSetting('maps_uri'),
            "token_uri": pluginSetting('token_uri'),
            "username": username,
            "password": password,
            "authcfg": pluginSetting('authcfg'),
            "project_template": pluginSetting('project_template'),
            "enabled": pluginSetting('enabled')
        }
        wizard = SetupWizard(settings)
        if QDialog.Accepted == wizard.exec_():
            # Process the results
            settings = wizard.settings
            if not settings.get('has_error'):
                setPluginSetting('enabled', False)
                utils.unset_default_project()
                authcfg = None
                if settings.get('enabled'):
                    try:
                        # Create the authcfg (or use existing)
                        if (settings.get('use_current_authcfg') and
                                settings.get('authcfg') is not None and
                                utils.get_authcfg(settings.get('authcfg')) is not None):
                            authcfg = settings.get('authcfg')
                        else:
                            authcfg = utils.setup_oauth(settings.get('username'), settings.get('password'), settings.get('token_uri'), None)
                        if authcfg is None:
                            raise BasemapsConfigError(self.tr("Could not find or create a valid authentication configuration!"))
                        # It shouldn't be empty but ...
                        if settings.get('selected') == '':
                            raise BasemapsConfigError(self.tr("You need to select at least one base map!"))
                        selected = [m for m in settings.get('selected').split('#') if m != '']
                        template = settings.get('project_template')
                        if template == '' or template is None:
                            template = PROJECT_DEFAULT_TEMPLATE
                        if not os.path.isfile(template):
                            raise BasemapsConfigError(self.tr("The project template is missing or invalid: '%s'" % template))
                        prj = utils.create_default_project([m for m in settings.get('available_maps') if m['name'] in selected], template, authcfg)
                        if prj is None or prj == '':
                            raise BasemapsConfigError(self.tr("Could not create a valid default project from the template '%s'!" % template))
                        utils.set_default_project(prj)
                        # Store settings
                        setPluginSetting('enabled', True)
                        setPluginSetting('authcfg', authcfg)
                        setPluginSetting('selected', settings.get('selected'))
                        self.iface.messageBar().pushMessage(self.tr("Basemaps setup success"), self.tr("Basemaps are now ready to use!"), level=QgsMessageBar.INFO)
                    except BaseException as e:
                        self.iface.messageBar().pushMessage(self.tr("Basemaps setup error"), e.message, level=QgsMessageBar.CRITICAL)
                    except Exception as e:
                        self.iface.messageBar().pushMessage(self.tr("Basemaps unhandled exception"), "%s" % e, level=QgsMessageBar.CRITICAL)
        else:  # Cancel or close
            pass
        setPluginSetting('first_time_setup_done', True)

    def initGui(self):

        helpIcon = QgsApplication.getThemeIcon('/mActionHelpAPI.png')
        self.helpAction = QAction(helpIcon, "Help...", self.iface.mainWindow())
        self.helpAction.setObjectName("boundlessbasemapsHelp")
        self.helpAction.triggered.connect(lambda: webbrowser.open_new(
                        "file://" + os.path.join(os.path.dirname(__file__), "docs", "html", "index.html")))
        self.iface.addPluginToMenu("Basemaps", self.helpAction)

        # Add setup action
        setupIcon = QgsApplication.getThemeIcon('/mActionOptions.svg')
        self.setupAction = QAction(setupIcon, "Setup...", self.iface.mainWindow())
        self.setupAction.setObjectName("boundlessbasemapssetup")
        self.setupAction.triggered.connect(self.setup)
        self.iface.addPluginToMenu("Basemaps", self.setupAction)

        addSettingsMenu("Basemaps")
        addAboutMenu("Basemaps")

    def unload(self):
        try:
            from .tests import testerplugin
            from qgistester.tests import removeTestModule
            removeTestModule(testerplugin, "boundlessbasemaps")
        except:
            pass

        self.iface.removePluginMenu("boundlessbasemaps", self.helpAction)
        self.iface.removePluginMenu("boundlessbasemaps", self.setupAction)
        removeSettingsMenu("Basemaps")
        removeAboutMenu("Basemaps")

    def run(self):
        self.setup()
