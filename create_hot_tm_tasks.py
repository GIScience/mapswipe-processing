#!/bin/python
# -*- coding: UTF-8 -*-
# Author: B. Herfort, 2016
# Modified by: M. Reinmuth
########################################################################################################################

#import libs


import os  # Require module os for file/directory handling
import logging
from distutils.dir_util import mkpath
import math # calculations etc
import numpy as np#arrays
from osgeo import ogr, osr #handling shapefiles
from shapely.wkt import dumps, loads
from shapely.ops import snap
from math import ceil

from geojson_functions import load_geom_from_geojson, save_geom_as_geojson
from tile_functions import *

import argparse
# define arguments that can be passed by the user
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-p', '--projects', nargs='+', required=None, default=None, type=int,
                    help='project id of the project to process. You can add multiple project ids.')
parser.add_argument('-d', '--data_dir', required=True, type=str,
                    help='data location')
parser.add_argument('-t', '--output_type', nargs='?', default='geojson',choices=['geojson', 'shp'])

########################################################################################################################

def GetSlice(polygon_to_slice, size):
    slice_collection = ogr.Geometry(ogr.wkbGeometryCollection)

    # get extent of geometry
    extent_pol = polygon_to_slice.GetEnvelope()
    xmin = extent_pol[0]
    xmax = extent_pol[1]
    ymin = extent_pol[2]
    ymax = extent_pol[3]

    zoom = 18
    # get upper left left tile coordinates
    pixel = lat_long_zoom_to_pixel_coords(ymax, xmin, zoom)
    tile = pixel_coords_to_tile_address(pixel.x, pixel.y)

    TileX_left = tile.x
    TileY_top = tile.y

    # get lower right tile coordinates
    pixel = lat_long_zoom_to_pixel_coords(ymin, xmax, zoom)
    tile = pixel_coords_to_tile_address(pixel.x, pixel.y)

    TileX_right = tile.x
    TileY_bottom = tile.y

    TileWidth = abs(TileX_right - TileX_left)
    TileHeight = abs(TileY_top - TileY_bottom)

    TileY = TileY_top
    TileX = TileX_left

    # get rows
    rows = int(ceil(TileHeight / size))
    # logging.warning rows
    # get columns
    cols = int(ceil(TileWidth / size))
    # logging.warning cols

    # define zoom
    zoom = 18

    ############################################################

    for i in range(0, rows + 1):
        TileX = TileX_left
        for j in range(0, cols + 1):

            # Calculate lat, lon of upper left corner of tile
            PixelX = TileX * 256
            PixelY = TileY * 256
            MapSize = 256 * math.pow(2, zoom)
            x = (PixelX / MapSize) - 0.5
            y = 0.5 - (PixelY / MapSize)
            lon_left = round((360 * x), 8)
            lat_top = round((90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi), 8)

            PixelX = (TileX + 30) * 256
            PixelY = (TileY + 30) * 256

            MapSize = 256 * math.pow(2, zoom)
            x = (PixelX / MapSize) - 0.5
            # logging.warning x
            # logging.warning y
            y = 0.5 - (PixelY / MapSize)
            lon_right = round((360 * x), 8)
            lat_bottom = round((90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi), 8)

            # logging.warning lon_right
            # logging.warning lat_bottom

            # Create Geometry
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(lon_left, lat_top)
            ring.AddPoint(lon_right, lat_top)
            ring.AddPoint(lon_right, lat_bottom)
            ring.AddPoint(lon_left, lat_bottom)
            ring.AddPoint(lon_left, lat_top)
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
            # logging.warning poly

            snapped_polygon_to_slice_ogr = snap_ogr_geometries(polygon_to_slice, poly, 0.00001)
            sliced_poly = poly.Intersection(snapped_polygon_to_slice_ogr)

            # Check if it is a polygon
            if sliced_poly.GetGeometryName() == "POLYGON":
                if sliced_poly.GetArea() < (1 * pow(10, -10)):
                    continue
                else:
                    slice_collection.AddGeometry(sliced_poly)

            # Check if it is a Multipolygon
            if sliced_poly.GetGeometryName() == "MULTIPOLYGON":
                for l in range(0, sliced_poly.GetGeometryCount()):
                    lo = sliced_poly.GetGeometryRef(l)
                    if lo.GetGeometryName() == "POLYGON":
                        # there are some crazy small polygons...
                        if lo.GetArea() < (1 * pow(10, -10)):
                            continue
                        else:
                            slice_collection.AddGeometry(lo)

            # Check if it is a Geometry Collection
            if sliced_poly.GetGeometryName() == "GEOMETRYCOLLECTION":
                for l in range(0, sliced_poly.GetGeometryCount()):
                    lo = sliced_poly.GetGeometryRef(l)
                    if lo.GetGeometryName() == "POLYGON":
                        # there are some crazy small polygons...
                        if lo.GetArea() < (1 * pow(10, -10)):
                            continue
                        else:
                            slice_collection.AddGeometry(lo)
                    if lo.GetGeometryName() == "MULTIPOLYGON":
                        for k in range(0, lo.GetGeometryCount()):
                            ko = lo.GetGeometryRef(l)
                            if ko.GetGeometryName() == "POLYGON":
                                # there are some crazy small polygons...
                                if ko.GetArea() < (1 * pow(10, -10)):
                                    continue
                                else:
                                    slice_collection.AddGeometry(ko)
            ####################
            TileX = TileX + size

        #####################
        TileY = TileY + size
    return slice_collection


def snap_ogr_geometries(geom_a, geom_b, tolerance):

    shapely_polygon_to_slice = loads(geom_a.ExportToWkt())
    shapely_poly = loads(geom_b.ExportToWkt())

    snapped_polygon_to_slice = snap(shapely_polygon_to_slice, shapely_poly, tolerance)
    snapped_polygon_to_slice_ogr = ogr.CreateGeometryFromWkt(dumps(snapped_polygon_to_slice))

    return snapped_polygon_to_slice_ogr


def GetGrid(polygon_to_grid):
    grid_collection = ogr.Geometry(ogr.wkbGeometryCollection)

    # get extent of geometry
    extent_pol = polygon_to_grid.GetEnvelope()
    xmin = extent_pol[0]
    xmax = extent_pol[1]
    ymin = extent_pol[2]
    ymax = extent_pol[3]

    zoom = 18
    # get upper left left tile coordinates
    pixel = lat_long_zoom_to_pixel_coords(ymax, xmin, zoom)
    tile = pixel_coords_to_tile_address(pixel.x, pixel.y)

    TileX_left = tile.x
    TileY_top = tile.y

    # get lower right tile coordinates
    pixel = lat_long_zoom_to_pixel_coords(ymin, xmax, zoom)
    tile = pixel_coords_to_tile_address(pixel.x, pixel.y)

    TileX_right = tile.x
    TileY_bottom = tile.y


    TileWidth = abs(TileX_right - TileX_left)
    TileHeight = abs(TileY_top - TileY_bottom)

    TileY = TileY_top
    TileX = TileX_left

    # get rows
    rows = int(ceil(TileHeight / 3))
    #logging.warning rows
    # get columns
    cols = int(ceil(TileWidth / 3))
    #logging.warning cols

    # define zoom
    zoom = 18

    ############################################################

    for i in range(0,rows+1):
        TileX = TileX_left
        for j in range(0,cols+1):

            # Calculate lat, lon of upper left corner of tile
            PixelX = TileX * 256
            PixelY = TileY * 256
            MapSize = 256*math.pow(2,zoom)
            x = (PixelX / MapSize) - 0.5
            y = 0.5 - (PixelY / MapSize)
            lon_left = round((360 * x), 8)
            lat_top = round((90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi), 8)

            PixelX = (TileX+3) * 256
            PixelY = (TileY+3) * 256


            MapSize = 256*math.pow(2,zoom)
            x = (PixelX / MapSize) - 0.5
            #logging.warning x
            #logging.warning y
            y = 0.5 - (PixelY / MapSize)
            lon_right = round((360 * x), 8)
            lat_bottom = round((90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi), 8)

            #logging.warning lon_right
            #logging.warning lat_bottom

            # Create Geometry
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(lon_left, lat_top)
            ring.AddPoint(lon_right, lat_top)
            ring.AddPoint(lon_right, lat_bottom)
            ring.AddPoint(lon_left, lat_bottom)
            ring.AddPoint(lon_left, lat_top)
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
            #logging.warning poly

            grid_collection.AddGeometry(poly)
            TileX = TileX + 3
        TileY = TileY + 3
    return grid_collection


def IntersectWithGrid(poly, grid):
    intersection_coll = ogr.Geometry(ogr.wkbGeometryCollection)
    # loop throguh grid features
    for e in range(0, grid.GetGeometryCount()):
        grid_geom = grid.GetGeometryRef(e)
        # check if geometries are intersecting
        #if grid_geom.Intersects(poly) == False:
        if grid_geom.Intersects(poly) == False:
            continue
        # compute the geometries

        poly = snap_ogr_geometries(poly, grid_geom, 0.000000001)

        intersection = grid_geom.Intersection(poly)  # intersection of grid collection and source polygon caused errors
        # check if the outcome of intersection is a multippolygon
        if intersection is None:
            continue
        elif intersection.GetGeometryName() == "POLYGON":
        # store geometry
            # there are some crazy small polygons...
            if intersection.GetArea() < (1*pow(10,-10)):
                continue
            else:
                intersection_coll.AddGeometry(intersection)

        if intersection.GetGeometryName() == "MULTIPOLYGON" or intersection.GetGeometryName() == "GEOMETRYCOLLECTION":
            # loop through every containing polygon and store it
            for l in range(0, intersection.GetGeometryCount()):
                lo = intersection.GetGeometryRef(l)
                if lo.GetGeometryName() == "POLYGON":
                    # there are some crazy small polygons...
                    if lo.GetArea() < (1*pow(10,-10)):
                        continue
                    else:
                        intersection_coll.AddGeometry(lo)

    return intersection_coll


def MergeSmallestNeighbour(inputcollection):
    geom_area = []
    output_coll = ogr.Geometry(ogr.wkbGeometryCollection)

    for f in range(0, inputcollection.GetGeometryCount()):
        h = inputcollection.GetGeometryRef(f)

        h_area = h.GetArea()
        #logging.warning(h_area)
        geom_area.append(h_area)
        #output_coll.AddGeometry(h)

    # create array
    geom_area_arr = np.array(geom_area)
    sorted_array = np.argsort(geom_area)

    skiplist = []
    for j in sorted_array:
        #logging.warning(j)
        g = inputcollection.GetGeometryRef(int(j))
        area = g.GetArea()
        #logging.warning('sorted geometrys: %s' % area)


        edge = 0
        # reset union process flag
        s = 0
        # skip already processed features
        if j in skiplist:
            continue

        for u in sorted_array:

            gg = inputcollection.GetGeometryRef(int(u))
            if u == j:
                continue
            if u in skiplist:
                continue

            if g.Intersects(gg) == False:
                continue
            else:
                if g.Intersection(gg).GetGeometryName() != "LINESTRING":
                    continue
                else:
                    temp_edge = g.Intersection(gg).Length()
                    # logging.warning (temp_edge)

                    if (g.GetArea() + gg.GetArea()) > (2.5*pow(10,-5)):
                        continue

                    if edge < temp_edge:
                        edge = temp_edge
                        # logging.warning(edge)
                        # save geometrie for union
                        fingeom = gg
                        # save index for skip
                        union_target_idx = u
                        # set union process flag
                        s = 1
                        continue

        if s == 0:
            # add geometry to final collection
            output_coll.AddGeometry(g)
            continue
        # calculate union of oriogin geom and neighbor
        union = g.Union(fingeom)
        # save result in final collection
        output_coll.AddGeometry(union)
        # append the list with processed geometries
        skiplist.append(union_target_idx)
        skiplist.append(int(j))

    return output_coll


def create_project_data_dict(project_id_list, data_dir):

    project_data_dict = {}

    for project_id in project_id_list:

        project_data_file = '{data_dir}/{project_id}/yes_maybe_{project_id}.geojson'.format(
            data_dir=data_dir,
            project_id=project_id
        )
        if not os.path.isfile(project_data_file):
            continue

        ogr_geometry_collection = load_geom_from_geojson(project_data_file)
        project_data_dict[project_id] = {
            "yes_maybe": ogr_geometry_collection
        }

    return project_data_dict


def create_geofile(geometries, outfile, output_type):
    # set driver for shapefile or geojson
    if output_type == 'shp':
        driver = ogr.GetDriverByName('ESRI Shapefile')
    elif output_type == 'geojson':
        driver = ogr.GetDriverByName('GeoJSON')
    # define spatial Reference
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    if os.path.exists(outfile):
        driver.DeleteDataSource(outfile)
    dataSource = driver.CreateDataSource(outfile)
    # create layer
    layer = dataSource.CreateLayer(outfile, srs, geom_type=ogr.wkbPolygon)

    # create fields
    field_id = ogr.FieldDefn('id', ogr.OFTString)
    layer.CreateField(field_id)

    counter = 0
    for geom in geometries:
        counter += 1
        # init feature
        featureDefn = layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        # create polygon from wkt and set geometry
        feature.SetGeometry(geom)
        # set other attributes
        feature.SetField('id', counter)
        # add feature to layer
        layer.CreateFeature(feature)

    layer = None
    dataSoure = None
    logging.warning('created outifle: %s.' % outfile)


def save_project_data(final_project_data_dict, output_path, output_type):

    for project_id, vals in final_project_data_dict.items():
        # save yes maybe
        final_output_path = '{output_path}/{project_id}'.format(
            output_path=output_path,
            project_id=project_id
        )

        # check if a data folder already exists
        if not os.path.exists(final_output_path):
            mkpath(final_output_path)
            logging.warning('Added the output folder')

        outfile = '{final_output_path}/hot_tm_tasks_{project_id}.{output_type}'.format(
            final_output_path=final_output_path,
            project_id=project_id,
            output_type=output_type

        )
        create_geofile(final_project_data_dict[project_id], outfile, output_type)


########################################################################################################################


def create_hot_tm_tasks(project_data_dict):


    final_project_data_dict = {}

    for project_id, project_data in project_data_dict.items():

        ogr_geometry_collection = project_data['yes_maybe']
        logging.warning('project %s, start create_hot_tm_tasks function' % project_id)

        # create output geometry collections
        final_coll = ogr.Geometry(ogr.wkbGeometryCollection)
        logging.warning('got %s geometries in input geometry collection.' % ogr_geometry_collection.GetGeometryCount())

        # loop through every geometry in given input geometry collection
        count = 0
        for geom in ogr_geometry_collection:
            count += 1
            slice_collection = GetSlice(geom, 30)
            for feature in slice_collection:
                # start grid function
                gridCollection = GetGrid(feature)
                intersection_coll = IntersectWithGrid(feature, gridCollection)
                # Merge Neighbours
                pre_step_0 = MergeSmallestNeighbour(intersection_coll)
                pre_step_1 = MergeSmallestNeighbour(pre_step_0)
                pre_step = MergeSmallestNeighbour(pre_step_1)
                for q in range(0, pre_step.GetGeometryCount()):
                    final_geom = pre_step.GetGeometryRef(q)
                    final_coll.AddGeometry(final_geom)

        final_project_data_dict[project_id] = final_coll

    return final_project_data_dict


########################################################################################################################
if __name__ == '__main__':
    logging.basicConfig(filename='create_hot_tm_tasks.log',
                        level=logging.WARNING,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M:%S',
                        filemode='a'
                        )

    logging.getLogger().addHandler(logging.StreamHandler())

    try:
        args = parser.parse_args()
    except:
        logging.warning('have a look at the input arguments, something went wrong there.')

    project_data_dict = create_project_data_dict(args.projects, args.data_dir)
    final_project_data_dict = create_hot_tm_tasks(project_data_dict)
    save_project_data(final_project_data_dict, args.data_dir, 'geojson')
