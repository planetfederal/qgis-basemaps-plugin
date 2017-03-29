# -*- coding: utf-8 -*-

"""
***************************************************************************
    setupwizard.py
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

Basemaps configuration wizard

"""
import os
import sys

__author__ = 'Alessandro Pasotti'
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

from qgis.PyQt.QtWidgets import (QWizard, QWizardPage, QLabel, QVBoxLayout,
                                 QLineEdit, QGridLayout, QCheckBox,
                                 QButtonGroup, QRadioButton, QGroupBox,
                                 QPushButton)
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.PyQt.QtCore import QSize
from boundlessbasemaps import utils


class WizardPage(QWizardPage):
    """Common behaviors for the wizard pages:
    - store an error message to be shown directly in the page"""

    def __init__(self, settings, parent=None):
        super(WizardPage, self).__init__(parent)
        self.settings = settings
        self.imgpath = os.path.join(os.path.dirname(__file__), os.path.pardir, "images")
        self.error_msg = None
        self.error_widget = QLabel()
        self.error_widget.setWordWrap(True)
        self.error_widget.setObjectName('wizard_error_widget')
        self.error_widget.hide()

    def error(self):
        return self.error_msg

    def set_error(self, message):
        self.error_msg = message

    def initializePage(self):
        """This will call setup()"""
        self.error_widget.hide()
        try:
            self.setup()
        except AttributeError:
            pass
        # Check for error messages
        if self.error() is not None:
            self.error_widget.setText("<b style='color:red'>%s</b>" % self.error_msg)
            if not self.layout():
                    self.setLayout(QVBoxLayout())
            self.layout().addWidget(self.error_widget)
            self.error_widget.show()

    def add_watermark(self):
        self.bg = QPixmap(os.path.join(self.imgpath, "wizard_watermark.png")).scaled(QSize(300, 600))
        self.setPixmap(QWizard.WatermarkPixmap, self.bg)


    def cleanupPage(self):
        self.set_error(None)


class IntroPage(WizardPage):
    """Intro page for wizard"""

    def __init__(self, settings, parent=None):
        super(IntroPage, self).__init__(settings, parent)

        self.setTitle(self.tr("Boundless base layers"))
        self.setSubTitle(self.tr("With Boundless Basemaps you can have a whole set of amazing online base layers automatically added to all your new projects!"))
        self.add_watermark()

        label = QLabel(self.tr("""This wizard will guide you through the configuration of Boundless Basemaps. This functionality uses a QGIS default project with pre-configured online basemaps. You can disable this functionality at any time from the Settings or re-running this wizard and unchecking the checkbox below."""))
        label.setWordWrap(True)

        self.optin = QCheckBox(self.tr("Yes: I'm in!"))
        self.optin.setChecked(settings.get('enabled', True))
        self.registerField('enabled', self.optin)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.optin)
        self.setLayout(layout)

    def nextId(self):
        if self.optin.isChecked():
            # If we do have a valid auth configuration let's ask the user
            try:
                if utils.get_authcfg(self.settings.get('authcfg')):
                    return SetupWizard.ConfirmCredentialsPage
                del(self.settings['authcfg'])
            except KeyError:
                pass
            if self.settings.get('username') is not None and self.settings.get('password') is not None:
                return SetupWizard.MapSelectionPage
            else:
                return SetupWizard.CredentialsPage
        else:
            return SetupWizard.ConclusionPage


class ConfirmCredentialsPage(WizardPage):
    """Confirm Credentials page for wizard"""

    def __init__(self, settings, parent=None):
        super(ConfirmCredentialsPage, self).__init__(settings, parent)
        self.setTitle("Use your current credentials configuration")
        self.setSubTitle("You already have an OAuth2 Connect credentials configuration: do you want to use it?")

        bh = QButtonGroup()
        self.optin = QRadioButton(self.tr("Use current configuration!"))
        self.optin.setChecked(True)
        self.optout = QRadioButton(self.tr("Create a new configuration!"))
        self.optout.setChecked(False)
        self.registerField('use_current_authcfg', self.optin)
        bh.addButton(self.optin)
        bh.addButton(self.optout)

        label = QLabel(self.tr("If you do not want to use your current configuration, you will be prompted to create a new one on the next step."))
        label.setWordWrap(True)
        self.label2 = QLabel()

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.label2)
        layout.addWidget(self.optin)
        layout.addWidget(self.optout)
        self.setLayout(layout)

    def initializePage(self):
        authcfg = utils.get_authcfg(self.settings.get('authcfg'))
        if authcfg is not None:
            # Store the ID, not the instance!
            self.settings['authcfg'] = authcfg.id()
            self.label2.setText(self.tr("Current configuration: [%s]<b>%s</b>") % (authcfg.id(), authcfg.name()))
        else:
            self.settings['authcfg'] = None
        super(ConfirmCredentialsPage, self).initializePage()

    def nextId(self):
        if self.optin.isChecked():
            return SetupWizard.MapSelectionPage
        else:
            return SetupWizard.CredentialsPage


class MapSelectionPage(WizardPage):
    """Map Selection page for wizard"""

    def __init__(self, settings, parent=None):
        super(MapSelectionPage, self).__init__(settings, parent)
        self.setTitle("Choose your Base Maps")
        self.setSubTitle("Here you can select which map you want to be added to your default project.")
        self.map_choices = []
        self.available_maps = None
        self.maplist_layout = QVBoxLayout()
        self.maplist = QGroupBox()
        self.maplist.setTitle(self.tr("Select your base maps!"))
        self.maplist.setFlat(True)

    def initializePage(self):
        # Get available maps
        if self.available_maps is None:
            selected = [e for e in self.settings.get('selected', "").split('###') if e != '']
            try:
                self.available_maps = utils.get_available_maps(self.settings.get('maps_uri'))
                self.settings['available_maps'] = self.available_maps
                self.map_choices = []
                if self.available_maps is not None and len(self.available_maps):
                    for m in self.available_maps:
                        w = QCheckBox("%(name)s" % m)
                        w.toggled.connect(self.completeChanged.emit)
                        self.map_choices.append(w)
                        w.setChecked((m['name'] in selected) if len(selected) else True)
                        self.maplist_layout.addWidget(w)
                    layout = QVBoxLayout()
                    layout.addWidget(self.maplist)
                    self.toggle_btn = QPushButton(self.tr("Toggle all"))

                    def _tg():
                        """Toggle"""
                        for w in self.map_choices:
                            w.setChecked(not w.isChecked())
                            self.completeChanged.emit()

                    self.toggle_btn.clicked.connect(_tg)
                    layout.addWidget(self.toggle_btn)
                    self.setLayout(layout)
                else:
                    self.set_error(self.tr("The list of available maps is empty!"))
            except Exception:
                self.set_error(self.tr("There was an error fetching the list of maps from the server! Please check your internet connection and retry later!"))
            self.maplist.setLayout(self.maplist_layout)
            super(MapSelectionPage, self).initializePage()

    def isComplete(self):
        """We need at least one map"""
        return super(MapSelectionPage, self).isComplete() and len([c for c in self.map_choices if c.isChecked()])

    def nextId(self):
        if self.error() is not None:
            return SetupWizard.FailurePage
        else:
            return SetupWizard.ConclusionPage


class CredentialsPage(WizardPage):
    """Credentials page for wizard"""
    def __init__(self, settings, parent=None):
        super(CredentialsPage, self).__init__(settings, parent)

        self.setTitle("Authentication configuration for Basemaps")
        self.setSubTitle("Please enter your Boundless Connect credentials to create the authentication configuration")

        nameLabel = QLabel("Username: ")
        self.username = QLineEdit()
        nameLabel.setBuddy(self.username)

        pwdLabel = QLabel(self.tr("&Password: "))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        pwdLabel.setBuddy(self.password)

        self.registerField("username*", self.username)
        self.registerField("password*", self.password)

        grid = QGridLayout()
        grid.addWidget(nameLabel, 0, 0)
        grid.addWidget(self.username, 0, 1)
        grid.addWidget(pwdLabel, 1, 0)
        grid.addWidget(self.password, 1, 1)

        label = QLabel("""You need to create an authentication configuration to access the online Basemaps. Please enter your credentials in the form below.""")
        label.setWordWrap(True)
        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addLayout(grid)
        self.setLayout(layout)


class ConclusionPage(WizardPage):
    """End page for wizard"""
    def __init__(self, settings, parent=None):
        super(ConclusionPage, self).__init__(settings, parent)

        self.setTitle(self.tr("Boundless base layers setup complete"))
        self.setSubTitle("")
        self.add_watermark()

        self.label = QLabel("")
        self.label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def nextId(self):
        return -1

    def initializePage(self):
        if self.field('enabled'):
            self.setSubTitle(self.tr("The Basemaps default project will now be created!"))
            self.label.setText(self.tr("""You can re-run this setup wizard at any time from the Plugins -> Basemaps -> Setup menu"""))
        else:
            self.setSubTitle(self.tr("You chose to not use the Basemaps."))
            self.label.setText(self.tr("If you change your mind, you can enable the Basemaps re-running this setup wizard from the Plugins -> Basemaps -> Setup menu"))
        super(ConclusionPage, self).initializePage()


class FailurePage(WizardPage):
    """End page for wizard"""
    def __init__(self, settings, parent=None):
        super(FailurePage, self).__init__(settings, parent)

        self.setTitle(self.tr("Boundless base layers setup errored"))
        self.setSubTitle(self.tr("There was an error setting up the maps!"))

        label = QLabel(self.tr("""Please have a look to the troubleshooting section in the manual and retry later!"""))
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

    def nextId(self):
        return -1


class SetupWizard(QWizard):
    """Main setup wizard

    The Wizard accepts a settings argument with pre-set value and return
    collected values in the same argument.

    Accepted settings:
    - enabled: if the basemaps are enabled
    - authcfg: optional (it is the id, not the instance!)
    - username: optional (if not authcfg)
    - password: optional (if not authcfg)
    - selected: optional
    - token_uri_: mandatory
    - maps_uri_: mandatory
    - project_template: optional

    Additional returned values in settings:
    - has_error: this is the only available setting in case of errors
    - available_maps
    - use_current_authcfg

    """

    NUM_PAGES = 6

    (IntroPage, ConfirmCredentialsPage, CredentialsPage, MapSelectionPage,
     ConclusionPage, FailurePage) = range(NUM_PAGES)

    def __init__(self, settings, parent=None):
        super(SetupWizard, self).__init__(parent)
        self.setWindowTitle("Boundles Base Layers Setup")
        self.settings = settings

        self.setPage(self.IntroPage, IntroPage(settings, self))
        self.setPage(self.ConfirmCredentialsPage, ConfirmCredentialsPage(settings, self))
        self.setPage(self.CredentialsPage, CredentialsPage(settings, self))
        self.setPage(self.MapSelectionPage, MapSelectionPage(settings, self))
        self.setPage(self.ConclusionPage, ConclusionPage(settings, self))
        self.setPage(self.FailurePage, FailurePage(settings, self))

        self.setStartId(self.IntroPage)

        if sys.platform.startswith('darwin'):
            self.setWizardStyle(QWizard.MacStyle)
        else:
            self.setWizardStyle(QWizard.ModernStyle)

        imgpath = os.path.join(os.path.dirname(__file__), os.path.pardir, "images")
        self.lg = QPixmap(QIcon(os.path.join(imgpath, "wizard_logo.svg")).pixmap(QSize(200, 200)))
        self.setPixmap(QWizard.LogoPixmap, self.lg)
        # Other possible wizard decorations
        #self.bn = QPixmap(QIcon(os.path.join(imgpath, "wizard_banner.svg")).pixmap(QSize(800, 300)))
        #self.setPixmap(QWizard.BannerPixmap, self.bn)
        #self.bg = QPixmap(os.path.join(imgpath, "wizard_background.png"))
        #self.setPixmap(QWizard.BackgroundPixmap, self.bg)

    def accept(self):
        """Collect user choices and update the settings dictionary
        The caller is responsible for the processing"""
        # Collect fields and data:
        if self.currentPage() == self.FailurePage:
            self.settings['has_error'] = True
        else:
            maps = [mc.text() for mc in self.page(self.MapSelectionPage).map_choices if mc.isChecked()]
            self.settings['selected'] = '#'.join(maps)
            self.settings['available_maps'] = self.settings.get('available_maps')
            self.settings['enabled'] = self.field('enabled')
            self.settings['use_current_authcfg'] = self.settings.get('authcfg') is not None and self.field('use_current_authcfg')
            if not self.settings['use_current_authcfg']:
                self.settings['username'] = self.field('username')
                self.settings['password'] = self.field('password')

        super(SetupWizard, self).accept()
