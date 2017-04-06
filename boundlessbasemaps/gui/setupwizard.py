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
                                 QTreeWidget, QTreeWidgetItem)
from qgis.PyQt.QtGui import QPixmap, QIcon
from qgis.PyQt.QtCore import Qt, QSize
from boundlessbasemaps import utils


class WizardPage(QWizardPage):
    """Common behaviors for the wizard pages:
    - store an error message to be shown directly in the page"""

    def __init__(self, settings, parent=None):
        super(WizardPage, self).__init__(parent)
        self.settings = settings
        self.setTitle(self.tr("Boundless Basemaps Setup"))
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


class IntroPage(WizardPage):
    """Intro page for wizard"""

    def __init__(self, settings, parent=None):
        super(IntroPage, self).__init__(settings, parent)

        self.setSubTitle(self.tr("With Boundless Basemaps, you can choose from a collection of premium maps to provide backdrops to your new projects!"))
        self.add_watermark()

        label = QLabel(self.tr("""This wizard will guide you through the configuration of Boundless Basemaps.<br>This functionality uses a QGIS default project with pre-configured online basemaps.<br>You can disable this functionality at any time re-running this wizard and unchecking the checkbox below."""))
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
            # If we do have a valid auth configuration, check it
            # if it's valid, jump to map selection
            if self.settings.get('authcfg') and utils.get_oauth_authcfg(self.settings.get('authcfg')):
                return SetupWizard.MapSelectionPage
            # If invalid or None: search for a valid default config
            elif utils.get_oauth_authcfg():
                return SetupWizard.ConfirmCredentialsPage
            # Nothing suitable? Invalidate the setting
            try:
                del(self.settings['authcfg'])
            except KeyError:
                pass
            if self.settings.get('username') and self.settings.get('password'):
                return SetupWizard.MapSelectionPage
            else:
                return SetupWizard.CredentialsPage
        else:
            return SetupWizard.ConclusionPage


class ConfirmCredentialsPage(WizardPage):
    """Confirm Credentials page for wizard"""

    def __init__(self, settings, parent=None):
        super(ConfirmCredentialsPage, self).__init__(settings, parent)
        self.setSubTitle(self.tr("Connect account confirmation: you already have a Connect account: do you want to use it?"))

        bh = QButtonGroup()
        self.optin = QRadioButton(self.tr("Use current account!"))
        self.optin.setChecked(True)
        self.optout = QRadioButton(self.tr("Use a different account!"))
        self.optout.setChecked(False)
        self.registerField('use_current_authcfg', self.optin)
        bh.addButton(self.optin)
        bh.addButton(self.optout)

        label = QLabel(self.tr("If you do not want to use your current account, you will be prompted to enter the credential for another account in the next step."))
        label.setWordWrap(True)
        self.label2 = QLabel()

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.label2)
        layout.addWidget(self.optin)
        layout.addWidget(self.optout)
        self.setLayout(layout)

    def initializePage(self):
        authcfg = utils.get_oauth_authcfg(self.settings.get('authcfg'))
        if authcfg is not None:
            # Store the ID, not the instance!
            self.settings['authcfg'] = authcfg.id()
            self.label2.setText(self.tr("Current Connect account: <b>%s</b>") % authcfg.name())
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
        self.setSubTitle(self.tr("Choose your base maps"))
        self.map_choices = []
        self.map_visible_choices = []
        self.available_maps = None
        self.maplist_layout = QVBoxLayout()
        label = QLabel(self.tr("Please select which base maps you want to be added to your new projects, check the \"Visible\" checkbox if you want the base map to be loaded by default."))
        label.setWordWrap(True)
        self.maplist_layout.addWidget(label)
        self.maplist = QGroupBox()
        #self.maplist.setTitle(self.tr("Select your base maps!"))
        self.maplist.setFlat(True)
        self.tree = None

    def initializePage(self):
        # Get available maps
        if self.available_maps is None:
            selected = [e for e in self.settings.get('selected', "").split('###') if e != '']
            visible = [e for e in self.settings.get('visible', "").split('###') if e != '']
            try:
                self.available_maps = utils.get_available_maps(self.settings.get('maps_uri'))
                self.settings['available_maps'] = self.available_maps
                self.map_choices = []
                if self.available_maps is not None and len(self.available_maps):
                    # Collect providers
                    providers = set()
                    for m in self.available_maps:
                        p = m['provider'] if 'provider' in m and m['provider'] else m['attribution']
                        if p not in providers:
                            providers.add(p)
                    providers = list(providers)
                    providers.sort()
                    # Build the tree
                    self.tree = QTreeWidget()
                    self.tree.setColumnCount(2)
                    self.tree.setHeaderLabels([self.tr("Available maps"), self.tr("Visible")])
                    root = QTreeWidgetItem(self.tree)
                    root.setText(0, self.tr("All maps"))
                    root.setFlags(root.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
                    root.setCheckState(0, Qt.Checked)

                    for p in providers:
                        parent = QTreeWidgetItem(root)
                        parent.setText(0, p)
                        parent.setFlags(parent.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
                        for m in self.available_maps:
                            if (m['provider'] if 'provider' in m  and m['provider'] else m['attribution']) == p:
                                child = QTreeWidgetItem(parent)
                                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                                child.setText(0, m['name'])
                                viscb = QCheckBox()
                                if len(visible):
                                    viscb.setChecked(m['name'] in visible)
                                else:
                                    viscb.setChecked(False)
                                self.tree.setItemWidget(child, 1, viscb)
                                self.map_visible_choices.append(viscb)
                                if m['description']:
                                    child.setToolTip(0, m['description'])
                                if len(selected):
                                    if m['name'] in selected:
                                        child.setCheckState(0, Qt.Checked)
                                    else:
                                        child.setCheckState(0, Qt.Unchecked)
                                else:
                                    child.setCheckState(0, Qt.Checked)
                                self.map_choices.append(child)

                    def set_visibility_state():
                        '''Control the status of the visibility widgets'''
                        i = 0
                        for w in self.map_choices:
                            self.map_visible_choices[i].setEnabled(self.map_choices[i].checkState(0) == Qt.Checked)
                            i += 1

                    set_visibility_state()
                    self.tree.model().dataChanged.connect(set_visibility_state)
                    self.tree.model().dataChanged.connect(self.completeChanged.emit)
                    self.tree.header().resizeSection(0, 600)
                    self.tree.header().resizeSection(1, 100)
                    self.tree.expandAll()
                    self.maplist_layout.addWidget(self.tree)
                else:
                    self.set_error(self.tr("The list of available maps is empty!"))
            except Exception as e:
                raise e
                self.set_error(self.tr("There was an error fetching the list of maps from the server! Please check your internet connection and retry later! Error: %s") % e)
            self.setLayout(self.maplist_layout)
            super(MapSelectionPage, self).initializePage()

    def isComplete(self):
        """We need at least one map"""
        return super(MapSelectionPage, self).isComplete() and len([c for c in self.map_choices if c.checkState(0) == Qt.Checked])

    def nextId(self):
        if self.error() is not None:
            return SetupWizard.FailurePage
        else:
            return SetupWizard.ConclusionPage


class CredentialsPage(WizardPage):
    """Credentials page for wizard"""
    def __init__(self, settings, parent=None):
        super(CredentialsPage, self).__init__(settings, parent)

        self.setSubTitle(self.tr("Connect login: in order to access the Basemaps you need a valid Connect account"))

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

        label = QLabel(self.tr("Please enter your Connect credentials in the form below."))
        label.setWordWrap(True)
        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addLayout(grid)
        self.setLayout(layout)


class ConclusionPage(WizardPage):
    """End page for wizard"""
    def __init__(self, settings, parent=None):
        super(ConclusionPage, self).__init__(settings, parent)

        self.setSubTitle(self.tr("Boundless Bsemaps setup complete"))
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
            self.label.setText(self.tr("""You can re-run this setup wizard at any time from the <tt>Plugins -> Basemaps -> Setup</tt> menu"""))
        else:
            self.setSubTitle(self.tr("You chose to not use the Basemaps."))
            self.label.setText(self.tr("If you change your mind, you can enable the Basemaps re-running this setup wizard from the <tt>Plugins -> Basemaps -> Setup</tt> menu"))
        super(ConclusionPage, self).initializePage()


class FailurePage(WizardPage):
    """End page for wizard in case of errors

    WARNING: this page is currently never reached, because the only possible
    point of failure is the map list fetch, but if that fails, the error
    is shown in the map selection page itself and the user can only choose
    cancel.
    I'm leaving the implementation here in case we change the workflow.
    """
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

    The Wizard accepts a mutable dictionary settings argument with
    pre-set value and return collected/modificed values in the same dictionary
    argument.

    Accepted settings:
    - enabled: if the basemaps are enabled
    - authcfg: optional (it is the id, not the instance!)
    - username: optional (if not authcfg)
    - password: optional (if not authcfg)
    - selected: optional (string with '###' delimited list of selected masps)
    - visible: optional (string with '###' delimited list of visible masps)
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
        self.setWindowTitle("Boundless Basemaps Setup")
        self.settings = settings

        self.setPage(self.IntroPage, IntroPage(settings, self))
        self.setPage(self.ConfirmCredentialsPage, ConfirmCredentialsPage(settings, self))
        self.setPage(self.CredentialsPage, CredentialsPage(settings, self))
        self.setPage(self.MapSelectionPage, MapSelectionPage(settings, self))
        self.setPage(self.ConclusionPage, ConclusionPage(settings, self))
        # Note: the following page cannot be reached in the current workflow
        #       left for future use
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
            maps = [mc.text(0) for mc in self.page(self.MapSelectionPage).map_choices if mc.checkState(0) == Qt.Checked]
            maps_visible = [self.page(self.MapSelectionPage).map_choices[i].text(0) for i in range(len(self.page(self.MapSelectionPage).map_visible_choices)) if self.page(self.MapSelectionPage).map_visible_choices[i].isChecked()]
            self.settings['selected'] = '###'.join(maps)
            self.settings['visible'] = '###'.join(maps_visible)
            self.settings['available_maps'] = self.settings.get('available_maps')
            self.settings['enabled'] = self.field('enabled')
            self.settings['use_current_authcfg'] = self.settings.get('authcfg') is not None and self.field('use_current_authcfg')
            if not self.settings['use_current_authcfg']:
                self.settings['username'] = self.field('username')
                self.settings['password'] = self.field('password')

        super(SetupWizard, self).accept()
