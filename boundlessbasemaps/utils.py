# -*- coding: utf-8 -*-

"""
***************************************************************************
    utils.py
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

Common functions for BCS API, authentication and templating.

"""

__author__ = 'Alessandro Pasotti'
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

import os
import json
import urllib2
from tempfile import mktemp
from qgis.core import (QgsAuthManager, QgsMapLayer, QgsRasterLayer,
                       QgsAuthMethodConfig, QgsApplication)
from qgis.PyQt.QtCore import QEventLoop, QUrl, QSettings
from qgis.gui import QgsFileDownloader


AUTHCFG_ID = "conect1"  # test id
AUTHCFG_NAME = "Boundless OAuth2 API"


def bcs_supported():
    """Check wether current QGIS installation has all requirements to
    consume BCS services, current checks
    - OAuth2 auth plugin is available
    """
    return 'OAuth2' in QgsAuthManager.instance().authMethodsKeys()


def set_default_project(content):
    """Create a new default project with the given content"""
    # TODO: check existing
    with open(os.path.join(QgsApplication.qgisSettingsDirPath(), 'project_default.qgs'), 'wb+') as f:
        f.write(content)
    settings = QSettings()
    settings.setValue('Qgis/newProjectDefault', True)


def unset_default_project():
    """Just store the setting"""
    settings = QSettings()
    settings.setValue('Qgis/newProjectDefault', False)


def get_oauth_authcfg(authcfg_id=AUTHCFG_ID):
    """Check if the given authcfg_id (or the default) exists, and if it's valid
    OAuth2, return the configuration or None"""
    # Handle empty strings
    if not authcfg_id:
        authcfg_id = AUTHCFG_ID
    configs = QgsAuthManager.instance().availableAuthMethodConfigs()
    if authcfg_id in configs \
        and configs[authcfg_id].isValid() \
        and configs[authcfg_id].method() == 'OAuth2':
        return configs[authcfg_id]
    return None


def setup_oauth(username, password, basemaps_token_uri, authcfg_id=AUTHCFG_ID, authcfg_name=AUTHCFG_NAME):
    """Setup oauth configuration to access the BCS API,
    return authcfg_id on success, None on failure
    """
    cfgjson = {
     "accessMethod" : 0,
     "apiKey" : "",
     "clientId" : "",
     "clientSecret" : "",
     "configType" : 1,
     "grantFlow" : 2,
     "password" : password,
     "persistToken" : False,
     "redirectPort" : '7070',
     "redirectUrl" : "",
     "refreshTokenUrl" : "",
     "requestTimeout" : '30',
     "requestUrl" : "",
     "scope" : "",
     "state" : "",
     "tokenUrl" : basemaps_token_uri,
     "username" : username,
     "version" : 1
    }

    if authcfg_id not in QgsAuthManager.instance().availableAuthMethodConfigs():
        authConfig = QgsAuthMethodConfig('OAuth2')
        authConfig.setId(authcfg_id)
        authConfig.setName(authcfg_name)
        authConfig.setConfig('oauth2config', json.dumps(cfgjson))
        if QgsAuthManager.instance().storeAuthenticationConfig(authConfig):
            return True
    else:
        authConfig = QgsAuthMethodConfig()
        QgsAuthManager.instance().loadAuthenticationConfig(authcfg, authConfig, True)
        authConfig.setName(authcfg_name)
        authConfig.setConfig('oauth2config', json.dumps(cfgjson))
        if QgsAuthManager.instance().updateAuthenticationConfig(authConfig):
            return True
    return None


def create_default_project(available_maps, project_template, authcfg=None):
    """Create a default project from a template and return it as a string"""
    layers = []
    for m in available_maps:
        connstring = u'type=xyz&url=%(url)s'
        if authcfg is not None:
            connstring += u'&authcfg=%(authcfg)s'
        layer = QgsRasterLayer(connstring % {
            'url': urllib2.quote(m['endpoint']),
            'authcfg': authcfg,
            'name': m['name'],
        }, m['name'], 'wms')
        layers.append(layer)
    if len(layers):
        xml = QgsMapLayer.asLayerDefinition(layers)
        maplayers = "\n".join(xml.toString().split("\n")[3:-3])
        layer_tree_layer = ""
        custom_order = ""
        legend_layer = ""
        layer_coordinate_transform = ""
        is_first = True
        for layer in layers:
            values =  {'name': layer.name(), 'id': layer.id(), 'visible': ('1' if is_first else '0'), 'checked': ('Qt::Checked'  if is_first else 'Qt::Unchecked')}
            custom_order += "<item>%s</item>" % layer.id()
            layer_tree_layer += """
            <layer-tree-layer expanded="1" checked="%(checked)s" id="%(id)s" name="%(name)s">
                <customproperties/>
            </layer-tree-layer>""" % values
            legend_layer += """
            <legendlayer drawingOrder="-1" open="true" checked="%(checked)s" name="%(name)s" showFeatureCount="0">
              <filegroup open="true" hidden="false">
                <legendlayerfile isInOverview="0" layerid="%(id)s" visible="%(visible)s"/>
              </filegroup>
            </legendlayer>""" % values
            layer_coordinate_transform += '<layer_coordinate_transform destAuthId="EPSG:3857" srcAuthId="EPSG:3857" srcDatumTransform="-1" destDatumTransform="-1" layerid="%s"/>' % layer.id()
            is_first = False
        tpl = ""
        with open(project_template, 'rb') as f:
            tpl = f.read()
        for tag in ['custom_order', 'layer_tree_layer', 'legend_layer', 'layer_coordinate_transform', 'maplayers']:
            tpl = tpl.replace("#%s#" % tag.upper(), locals()[tag])
        return tpl
    else:
        return None


def layer_is_supported(lyr):
    """Check wether the layer is supported by QGIS or by this plugin
    inverted y and vector tiles are not supported"""
    return (lyr['endpoint'].find('{-y}') == -1 and
            lyr['tileFormat'] == 'PNG' and
            lyr['standard'] == 'XYZ')


def get_available_maps(maps_uri):
    """Fetch the list of available and QGIS supported maps from BCS endpoint,
    apparently this API method does not require auth"""
    # For testing purposes, we can also access to a json file directly
    if not maps_uri.startswith('http'):
        return json.load(open(maps_uri))
    t = mktemp()
    q = QgsFileDownloader(QUrl(maps_uri), t)
    loop = QEventLoop()
    q.downloadExited.connect(loop.quit)
    loop.exec_()
    with open(t) as f:
        j = json.load(f)
    os.unlink(t)
    return [l for l in j if layer_is_supported(l)]
