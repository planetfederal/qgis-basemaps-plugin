#!/usr/bin/env python
# Tests for the QGIS Tester plugin. To know more see
# https://github.com/boundlessgeo/qgis-tester-plugin

import os
import re
import sys
import shutil
import unittest
import tempfile


MAPS_URI = "http://api.boundlessgeo.io/v1/basemaps/"
TOKEN_URI = "https://api.dev.boundlessgeo.io/v1/token/oauth/"
AUTHDB_MASTERPWD = "pass"


AUTHDBDIR = tempfile.mkdtemp()
os.environ['QGIS_AUTH_DB_DIR_PATH'] = AUTHDBDIR


try:
    from qgistester.test import Test
    from qgistester.utils import layerFromName
except:
    pass

from boundlessbasemaps import utils
from boundlessbasemaps.gui.setupwizard import SetupWizard
from qgis.core import QgsProject, QgsApplication, QgsAuthManager
from qgis.PyQt.QtCore import QFileInfo


def functionalTests():
    try:
        from qgistester.test import Test
        from qgistester.utils import layerFromName
    except:
        return []

    def sampleMethod(self):
        pass

    sampleTest = Test("Sample test")
    sampleTest.addStep("Sample step", _sampleMethod)

    return [sampleTest]


class BasemapsTest(unittest.TestCase):

    AUTHM = None

    def setUp(self):
        for c in self.authm.availableAuthMethodConfigs().values():
            if c.name() == utils.AUTHCFG_NAME:
                assert self.authm.removeAuthenticationConfig(c.id())
        if (not self.authm.masterPasswordIsSet()
                or not self.authm.masterPasswordHashInDb()):
            msg = 'Failed to store and verify master password in auth db'
            assert self.authm.setMasterPassword(self.mpass, True), msg

    @classmethod
    def setUpClass(cls):
        cls.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        cls.tpl_path = os.path.join(
            os.path.dirname(__file__), os.path.pardir, 'project_default.qgs.tpl')
        cls.authcfg = None
        cls.authm = QgsAuthManager.instance()
        assert not cls.authm.isDisabled(), cls.authm.disabledMessage()

        cls.mpass = AUTHDB_MASTERPWD  # master password

        db1 = QFileInfo(cls.authm.authenticationDbPath()).canonicalFilePath()
        db2 = QFileInfo(AUTHDBDIR + '/qgis-auth.db').canonicalFilePath()
        msg = 'Auth db temp path does not match db path of manager'
        assert db1 == db2, msg

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(AUTHDBDIR)
        except:
            pass

    def _standard_id(self, tpl):
        """Change the layer ids to XXXXXXXX"""
        tpl = re.sub(r'id="([^\d]+).*"', 'id="\g<1>XXXXXXX"', tpl)
        tpl = re.sub(
            r'<item>([^\d]+).*?</item>', '<item>\g<1>XXXXXXX</item>', tpl)
        tpl = re.sub(r'<id>([^\d]+).*?</id>', '<id>\g<1>XXXXXXX</id>', tpl)
        tpl = re.sub(r'authcfg=[a-z0-9]+', 'authcfg=YYYYYY', tpl)
        return tpl

    def test_utils_get_available_maps_online(self):
        self.assertTrue(utils.bcs_supported())
        maps = utils.get_available_maps(MAPS_URI)
        names = [m['name'] for m in maps]
        names.sort()
        self.assertEqual(names, [
                                 #u'Boundless Basemap',# unsupported
                                 u'Mapbox Dark',
                                 u'Mapbox Light',
                                 u'Mapbox Outdoors',
                                 u'Mapbox Satellite',
                                 u'Mapbox Satellite Streets',
                                 #u'Mapbox Street Vector Tiles', # unsupported
                                 u'Mapbox Streets',
                                 #u'Mapbox Traffic Vector Tiles'# unsupported
                                 ])

    def test_utils_get_available_maps(self):
        self.assertTrue(utils.bcs_supported())
        maps = utils.get_available_maps(os.path.join(self.data_dir,
                                                     'basemaps.json'))
        names = [m['name'] for m in maps]
        names.sort()
        self.assertEqual(names, [u'Boundless Basemap',
                                 u'Mapbox Dark',
                                 u'Mapbox Light',
                                 u'Mapbox Outdoors',
                                 u'Mapbox Satellite',
                                 u'Mapbox Satellite Streets',
                                 u'Mapbox Street Vector Tiles',
                                 u'Mapbox Streets',
                                 u'Mapbox Traffic Vector Tiles'])

    def test_utils_create_default_auth_project(self):
        """Use a auth project template"""
        self.assertTrue(utils.bcs_supported())
        prj = utils.create_default_project(
            utils.get_available_maps(
                os.path.join(self.data_dir, 'basemaps.json')),
            self.tpl_path,
            'abc123')
        prj = self._standard_id(prj)
        # Re-generate reference:
        # with open(os.path.join(self.data_dir, 'project_default_reference.qgs'), 'wb+') as f:
        #    f.write(prj)
        self.assertEqual(
            prj, open(os.path.join(self.data_dir, 'project_default_reference.qgs'), 'rb').read())

    def test_utils_create_default_project(self):
        """Use a no_auth project template for automated testing of valid project"""
        prj = utils.create_default_project(
            utils.get_available_maps(
                os.path.join(self.data_dir, 'basemaps_no_auth.json')),
            self.tpl_path)
        # Re-generate reference:
        # with open(os.path.join(self.data_dir, 'project_default_no_auth_reference.qgs'), 'wb+') as f:
        #    f.write(self._standard_id(prj))
        tmp = tempfile.mktemp('.qgs')
        with open(tmp, 'wb+') as f:
            f.write(prj)
        self.assertTrue(QgsProject.instance().read(QFileInfo(tmp)))
        self.assertEqual(self._standard_id(prj), open(
            os.path.join(self.data_dir, 'project_default_no_auth_reference.qgs'), 'rb').read())

    def test_create_oauth(self):
        """Create and authentication configuration"""
        authcfg = utils.setup_oauth('username', 'password', TOKEN_URI, None)
        self.assertIsNotNone(authcfg)

    def test_wizard(self):
        """Test the wizard dialog"""
        # Forge some settings:
        settings = {
            "token_uri": TOKEN_URI,
            "maps_uri": MAPS_URI,
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
        [c.setChecked(c.text().find('Street') != -1) for c in ms.map_choices]
        w.next()
        w.accept()
        # Check all
        self.assertTrue(w.settings.get('enabled'))
        self.assertIsNone(w.settings.get('authcfg'))
        self.assertFalse(w.settings.get('use_current_authcfg'))
        self.assertEquals(w.settings.get('selected'),
                          u'Mapbox Satellite Streets#Mapbox Streets')
        self.assertEquals(w.settings.get('username'), 'my_username')
        self.assertEquals(w.settings.get('password'), 'my_password')

    def test_wizard_no_selected(self):
        """Test the wizard dialog with no selected maps"""
        # Forge some settings:
        settings = {
            "token_uri": TOKEN_URI,
            "maps_uri": MAPS_URI,
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
        [c.setChecked(False) for c in ms.map_choices]
        w.next()
        w.accept()
        # Check all
        self.assertTrue(w.settings.get('enabled'))
        self.assertIsNone(w.settings.get('authcfg'))
        self.assertFalse(w.settings.get('use_current_authcfg'))
        self.assertEquals(w.settings.get('selected'), '')
        self.assertEquals(w.settings.get('username'), 'my_username')
        self.assertEquals(w.settings.get('password'), 'my_password')



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


if __name__ == '__main__':
    QgsApplication.setPrefixPath('/usr/', True)
    qgs = QgsApplication([], True)
    qgs.initQgis()
    unittest.main()
