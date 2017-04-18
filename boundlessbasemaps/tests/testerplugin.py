#!/usr/bin/env python
# Tests for the QGIS Tester plugin and for Travis CI.
# This test can be run from the command line as a normal
# python script

# To know more see
# https://github.com/boundlessgeo/qgis-tester-plugin

import os
import re
import sys
import shutil
import unittest
import tempfile


__author__ = 'Alessandro Pasotti'
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'


MAPS_URI = "https://api.test.boundlessgeo.io/v1/basemaps/"
PROVIDERS_URI = "https://api.dev.boundlessgeo.io/v1/basemaps/providers/"
TOKEN_URI = "https://api.test.boundlessgeo.io/v1/token/oauth/"
AUTHDB_MASTERPWD = "pass"
TEST_AUTHCFG_ID = "cone999"  # test id
TEST_AUTHCFG_NAME = "Boundless BCS API OAuth2 - TEST"
# To be used by command line tests, when inside QGIS, the AUTHDBDIR
# is not needed as the auth DB is initialized by QGIS authentication system
# initialization
AUTHDBDIR = None

try:
    from qgistester.test import Test
    from qgistester.utils import layerFromName
except:
    pass

from boundlessbasemaps import utils
from boundlessbasemaps.gui.setupwizard import *
from qgis.core import QgsProject, QgsApplication, QgsAuthManager
from qgis.PyQt.QtCore import QFileInfo, Qt


def functionalTests():
    try:
        from qgistester.test import Test
        from qgistester.utils import layerFromName
    except:
        return []

    return [] # or ...
    # ... define manual tests here:

    def sampleMethod(self):
        pass

    sampleTest = Test("Sample test")
    sampleTest.addStep("Sample step", sampleMethod)

    return [sampleTest]


class BasemapsTest(unittest.TestCase):

    AUTHM = None

    def setUp(self):
        for c in self.authm.availableAuthMethodConfigs().values():
            if c.id() == TEST_AUTHCFG_ID:
                assert self.authm.removeAuthenticationConfig(c.id())
        if (not self.authm.masterPasswordIsSet()
                or not self.authm.masterPasswordHashInDb()):
            if AUTHDBDIR is not None or not self.authm.masterPasswordHashInDb():
                msg = 'Failed to store and verify master password in auth db'
                assert self.authm.setMasterPassword(self.mpass, True), msg
            else:
                msg = 'Master password is not valid'
                assert self.authm.setMasterPassword(True), msg

    @classmethod
    def setUpClass(cls):
        cls.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        cls.local_maps_uri = os.path.join(cls.data_dir, 'basemaps.json')
        cls.local_providers_uri = os.path.join(cls.data_dir, 'providers.json')
        cls.tpl_path = os.path.join(
            os.path.dirname(__file__), os.path.pardir, 'project_default.qgs.tpl')
        cls.authcfg = None
        cls.authm = QgsAuthManager.instance()
        assert not cls.authm.isDisabled(), cls.authm.disabledMessage()
        cls.mpass = AUTHDB_MASTERPWD  # master password

        if AUTHDBDIR is not None:
            db1 = QFileInfo(cls.authm.authenticationDbPath()).canonicalFilePath()
            db2 = QFileInfo(AUTHDBDIR + '/qgis-auth.db').canonicalFilePath()
            msg = 'Auth db temp path does not match db path of manager'
            assert db1 == db2, msg

    @classmethod
    def tearDownClass(cls):
        if AUTHDBDIR is not None:
            try:
                shutil.rmtree(AUTHDBDIR)
            except:
                pass

    def _standard_id(self, tpl):
        """Change the layer ids to XXXXXXXX"""
        tpl = re.sub(r'id="([^\d]+)[^"]*"', 'id="\g<1>XXXXXXX"', tpl)
        tpl = re.sub(
            r'<item>([^\d]+).*?</item>', '<item>\g<1>XXXXXXX</item>', tpl)
        tpl = re.sub(r'<id>([^\d]+).*?</id>', '<id>\g<1>XXXXXXX</id>', tpl)
        tpl = re.sub(r'authcfg=[a-z0-9]+', 'authcfg=YYYYYY', tpl)
        return tpl

    def test_utils_get_available_maps(self):
        """Check available maps retrieval from local test json file"""
        self.assertTrue(utils.bcs_supported())
        maps = utils.get_available_maps(os.path.join(self.data_dir,
                                                     'basemaps.json'))
        names = [m['name'] for m in maps]
        names.sort()
        self.assertEqual(names, [
                                 u'Mapbox Dark',
                                 u'Mapbox Light',
                                 u'Mapbox Outdoors',
                                 u'Mapbox Satellite',
                                 u'Mapbox Satellite Streets',
                                 #u'Mapbox Street Vector Tiles',
                                 u'Mapbox Streets',
                                 #u'Mapbox Traffic Vector Tiles',
                                 u'Recent Imagery',
                                 ])

    def test_utils_get_available_providers(self):
        """Check available maps retrieval from local test json file"""
        self.assertTrue(utils.bcs_supported())
        maps = utils.get_available_providers(os.path.join(self.data_dir,
                                                     'providers.json'))
        names = [m['id'] for m in maps]
        names.sort()
        self.assertEqual(names, [u'boundless', u'digitalglobe', u'mapbox', u'planet'])

    def test_utils_create_default_auth_project(self):
        """Create the default project with authcfg"""
        self.assertTrue(utils.bcs_supported())
        visible_maps = ['Mapbox Light', 'Recent Imagery']
        prj = utils.create_default_project(
            utils.get_available_maps(
                os.path.join(self.data_dir, 'basemaps.json')),
            visible_maps,
            self.tpl_path,
            'abc123')
        prj = self._standard_id(prj)
        # Re-generate reference:
        #with open(os.path.join(self.data_dir, 'project_default_reference.qgs'), 'wb+') as f:
        #    f.write(prj)
        self.assertEqual(
            prj, open(os.path.join(self.data_dir, 'project_default_reference.qgs'), 'rb').read())

    def test_utils_create_default_project(self):
        """Use a no_auth project template for automated testing of valid project"""
        visible_maps = ['OSM Basemap B']
        prj = utils.create_default_project(
            utils.get_available_maps(
                os.path.join(self.data_dir, 'basemaps_no_auth.json')),
            visible_maps,
            self.tpl_path)
        # Re-generate reference:
        #with open(os.path.join(self.data_dir, 'project_default_no_auth_reference.qgs'), 'wb+') as f:
        #    f.write(self._standard_id(prj))
        tmp = tempfile.mktemp('.qgs')
        with open(tmp, 'wb+') as f:
            f.write(prj)
        self.assertTrue(QgsProject.instance().read(QFileInfo(tmp)))
        self.assertEqual(self._standard_id(prj), open(
            os.path.join(self.data_dir, 'project_default_no_auth_reference.qgs'), 'rb').read())

    def test_utils_create_oauth(self):
        """Create an authentication configuration"""
        self.assertEquals(utils.setup_oauth('username', 'password', TOKEN_URI, TEST_AUTHCFG_ID, TEST_AUTHCFG_NAME), TEST_AUTHCFG_ID)

    def test_wizard(self):
        """Test the wizard dialog full workflow"""
        # Forge some settings:
        settings = {
            "token_uri": TOKEN_URI,
            "maps_uri": self.local_maps_uri,
            "providers_uri": self.local_providers_uri,
            "visible": u'Mapbox Streets',
            "selected": u'Mapbox Satellite Streets###Mapbox Streets'
        }
        w = SetupWizard(settings)
        w.show()
        # Go to CredentialsPage
        w.next()
        w.currentPage().username.setText('my_username')
        w.currentPage().password.setText('my_password')
        # Go to map selection page
        w.next()
        w.next()
        w.accept()
        # Check all
        self.assertTrue(w.settings.get('enabled'))
        self.assertIsNone(w.settings.get('authcfg'))
        self.assertFalse(w.settings.get('use_current_authcfg'))
        self.assertEquals(w.settings.get('selected'),
                          u'Mapbox Satellite Streets###Mapbox Streets')
        self.assertEquals(w.settings.get('visible'),
                          u'Mapbox Streets')
        self.assertEquals(w.settings.get('username'), 'my_username')
        self.assertEquals(w.settings.get('password'), 'my_password')

    def test_wizard_no_selected(self):
        """Test the wizard dialog with no selected maps"""
        # Forge some settings:
        settings = {
            "token_uri": TOKEN_URI,
            "maps_uri": self.local_maps_uri,
            "providers_uri": self.local_providers_uri,
        }
        w = SetupWizard(settings)
        w.show()
        # Go to CredentialsPage
        w.next()
        w.currentPage().username.setText('my_username')
        w.currentPage().password.setText('my_password')
        # Go to map selection page
        w.next()
        ms = w.currentPage()
        # Check Streets
        [c.setCheckState(0, Qt.Unchecked) for c in ms.map_choices]
        w.next()
        w.accept()
        # Check all
        self.assertTrue(w.settings.get('enabled'))
        self.assertIsNone(w.settings.get('authcfg'))
        self.assertFalse(w.settings.get('use_current_authcfg'))
        self.assertEquals(w.settings.get('selected'), '')
        self.assertEquals(w.settings.get('username'), 'my_username')
        self.assertEquals(w.settings.get('password'), 'my_password')

    def test_wizard_pre_defined_authcfg(self):
        """Test the wizard dialog with valid authcfg"""
        # Forge some settings:
        self.assertEquals(utils.setup_oauth('username', 'password', TOKEN_URI, TEST_AUTHCFG_ID, TEST_AUTHCFG_NAME), TEST_AUTHCFG_ID)
        settings = {
            "token_uri": TOKEN_URI,
            "maps_uri": self.local_maps_uri,
            "providers_uri": self.local_providers_uri,
            "authcfg": TEST_AUTHCFG_ID
        }
        w = SetupWizard(settings)
        w.show()
        # Go to map selection page
        w.next()
        ms = w.currentPage()
        # Check Streets
        [c.setCheckState(0, (Qt.Checked if c.text(0).find('Street') != -1 else Qt.Unchecked)) for c in ms.map_choices]
        w.next()
        w.accept()
        # Check all
        self.assertTrue(w.settings.get('enabled'))
        self.assertEquals(w.settings.get('authcfg'), settings['authcfg'])
        self.assertTrue(w.settings.get('use_current_authcfg'))
        self.assertEquals(w.settings.get('selected'),
                          u'Mapbox Satellite Streets###Mapbox Streets')
        self.assertIsNone(w.settings.get('username'))
        self.assertIsNone(w.settings.get('password'))


    def test_wizard_pre_defined_invalid_authcfg(self):
        """Test the wizard dialog with invalid authcfg"""
        # Forge some settings:
        settings = {
            "token_uri": TOKEN_URI,
            "maps_uri": self.local_maps_uri,
            "providers_uri": self.local_providers_uri,
            "authcfg": 'fffffff',
        }
        w = SetupWizard(settings)
        w.show()
        # Go to CredentialsPage
        w.next()
        self.assertIs(w.currentPage().__class__, CredentialsPage)
        w.currentPage().username.setText('my_username')
        w.currentPage().password.setText('my_password')
        # Go to map selection page
        w.next()
        self.assertIs(w.currentPage().__class__, MapSelectionPage)
        ms = w.currentPage()
        # Check Streets
        [c.setCheckState(0, (Qt.Checked if c.text(0).find('Street') != -1 else Qt.Unchecked)) for c in ms.map_choices]
        w.next()
        self.assertIs(w.currentPage().__class__, ConclusionPage)
        w.accept()
        # Check all
        self.assertTrue(w.settings.get('enabled'))
        self.assertIsNone(w.settings.get('authcfg'))
        self.assertFalse(w.settings.get('use_current_authcfg'))
        self.assertEquals(w.settings.get('selected'),
                          u'Mapbox Satellite Streets###Mapbox Streets')
        self.assertEquals(w.settings.get('username'), 'my_username')
        self.assertEquals(w.settings.get('password'), 'my_password')


    def test_wizard_pre_defined_username_password(self):
        """Test the wizard dialog with predefined username and password"""
        # Forge some settings:
        settings = {
            "token_uri": TOKEN_URI,
            "providers_uri": self.local_providers_uri,
            "maps_uri": self.local_maps_uri,
            "username": 'my_username',
            "password": 'my_password',
        }
        w = SetupWizard(settings)
        w.show()
        # Go to map selection page
        w.next()
        ms = w.currentPage()
        self.assertIs(ms.__class__, MapSelectionPage)
        # Check Streets

        [c.setCheckState(0, (Qt.Checked if c.text(0).find('Street') != -1 else Qt.Unchecked)) for c in ms.map_choices]
        w.next()
        w.accept()
        # Check all
        self.assertTrue(w.settings.get('enabled'))
        self.assertIsNone(w.settings.get('authcfg'))
        self.assertFalse(w.settings.get('use_current_authcfg'))
        self.assertEquals(w.settings.get('selected'),
                          u'Mapbox Satellite Streets###Mapbox Streets')
        self.assertEquals(w.settings.get('username'), settings.get('username'))
        self.assertEquals(w.settings.get('password'), settings.get('password'))


def pluginSuite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(BasemapsTest, 'test'))
    return suite


def unitTests():
    _tests = []
    _tests.extend(pluginSuite())
    return _tests

# run all tests, this function is automatically called by the travis CI
# from the qgis-testing-environment-docker system


def run_all():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(pluginSuite())


def _test_wizard_interactive():
    """For debugging"""
    settings = {
        "token_uri": TOKEN_URI,
        "maps_uri": MAPS_URI,
        "providers_uri": PROVIDERS_URI,
        "username": 'my_username',
        "password": 'my_password',
        "visible": 'Mapbox Light',
        "selected": 'Mapbox Light',
    }
    w = SetupWizard(settings)
    import pprint
    pprint.pprint(w.exec_())
    pprint.pprint(settings)


if __name__ == '__main__':
    AUTHDBDIR = tempfile.mkdtemp()
    os.environ['QGIS_AUTH_DB_DIR_PATH'] = AUTHDBDIR
    QgsApplication.setPrefixPath('/usr/', True)
    qgs = QgsApplication([], True)
    qgs.initQgis()
    try:
        sys.argv[1]
        _test_wizard_interactive()
    except:
        unittest.main()
