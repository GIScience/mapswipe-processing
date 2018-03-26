#!/bin/python
# -*- coding: UTF-8 -*-
# Authors: B. Herfort, M. Reinmuth, M. Dollinger, 2018
########################################################################################################################
# import libs

import os
from osgeo import ogr, osr #handling shapefiles

########################################################################################################################
# load and save geojson

def load_geom_from_geojson(infile):
    driver = ogr.GetDriverByName('GeoJSON')
    datasource = driver.Open(infile, 0)
    layer = datasource.GetLayer()
    geomcol = ogr.Geometry(ogr.wkbGeometryCollection)
    for feature in layer:
        geomcol.AddGeometry(feature.GetGeometryRef())

    return geomcol


def save_geom_as_geojson(geomcol, outfile):
    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)

    driver = ogr.GetDriverByName('GeoJSON')
    if os.path.exists(outfile):
        driver.DeleteDataSource(outfile)
    data_final = driver.CreateDataSource(outfile)
    layer_final = data_final.CreateLayer(outfile, wgs, geom_type=ogr.wkbPolygon)
    fdef_final = layer_final.GetLayerDefn()

    # save each polygon as feature in layer
    for p in range(0, geomcol.GetGeometryCount()):
        da = geomcol.GetGeometryRef(p)
        da.FlattenTo2D()
        if da.GetGeometryName() == 'POLYGON':
            feature_final = ogr.Feature(fdef_final)
            feature_final.SetGeometry(da)
            layer_final.CreateFeature(feature_final)
            feature_final.Destroy

        elif da.GetGeometryName() == 'MULTIPOLYGON':
            for geom_part in da:
                feature_final = ogr.Feature(fdef_final)
                feature_final.SetGeometry(geom_part)
                layer_final.CreateFeature(feature_final)
                feature_final.Destroy
        else:
            print('other geometry type: %s' % da.GetGeometryName())
            print(da)
            continue

    geomcol = None
    data_final.Destroy()
