#!/bin/python
# -*- coding: UTF-8 -*-
# Author: B. Herfort, 2016
# Modified by: M. Reinmuth
########################################################################################################################

#import libs


import os  # Require module os for file/directory handling
import logging
import math
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

    logging.debug(extent_pol)

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


    logging.debug('cols: %s' % cols)
    logging.debug('rows: %s' % rows)

    # define zoom
    zoom = 18

    if rows < 1:
        rows = 1
    if cols < 1:
        cols = 1

    ############################################################

    for i in range(0, rows):
        TileX = TileX_left
        for j in range(0, cols):

            poly = create_grid_polygon(TileX, TileY, zoom, size)

            snapped_polygon_to_slice_ogr = snap_ogr_geometries(polygon_to_slice, poly, 0.000001)
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

    #print(shapely_polygon_to_slice.is_valid)
    #print(shapely_poly.is_valid)


    snapped_polygon_to_slice = snap(shapely_polygon_to_slice, shapely_poly, tolerance)
    snapped_polygon_to_slice_ogr = ogr.CreateGeometryFromWkt(dumps(snapped_polygon_to_slice))

    return snapped_polygon_to_slice_ogr


def create_grid_polygon(TileX, TileY, zoom, size):
    '''
    TileX, TileY --> correspong to Top left Tile
    size --> defines the width and height of the grid polygon
    e.g. size = 3 --> 3x3 tiles grid

    for a 3x3 tile grid we define polygon with 13 points
    (linearring starts and ends at "a")

    a----b----c----d
    |              |
    l              e
    |              |
    k              f
    |              |
    j----i----h----g
    '''
    logging.debug('TileX: %s, TileY: %s' % (TileX, TileY))

    pixel_coords = []
    lon_lat_coords = []
    grid_poly = ogr.Geometry(ogr.wkbPolygon)
    ring = ogr.Geometry(ogr.wkbLinearRing)

    PixelX = TileX * 256
    PixelY = TileY * 256
    pixel_coords.append([PixelX, PixelY])

    # start with the points on the top (e.g. "a"-"d" for 3x3 polygon)
    i = 0
    for i in range(1, size + 1):
        PixelX += 256
        # PixelY doesn't change
        pixel_coords.append([PixelX, PixelY])

    # proceed with the right points, that are not at the top (e.g. "e"-"g" for 3x3 polygon)
    i = 0
    for i in range(1, size + 1):
        # PixelX doesn't change
        PixelY += 256
        pixel_coords.append([PixelX, PixelY])

    # proceed with the bottom points (e.g. "h"-"j" for 3x3 polygon)
    i = 0
    for i in range(1, size + 1):
        PixelX -= 256
        # PixelY doesn't change
        pixel_coords.append([PixelX, PixelY])

    # proceed with the left points (e.g. "k"-"a" for 3x3 polygon)
    i = 0
    for i in range(1, size + 1):
        # PixelX doesn't change
        PixelY -= 256
        pixel_coords.append([PixelX, PixelY])

    # compute lon lat coordinates
    for PixelX, PixelY in pixel_coords:
        MapSize = 256 * math.pow(2, zoom)
        x = (PixelX / MapSize) - 0.5
        y = 0.5 - (PixelY / MapSize)
        lon = (360 * x)
        lat = (90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi)
        lon_lat_coords.append([lon, lat])

    # add lon lat coordinates to ring
    for lon, lat in lon_lat_coords:
        ring.AddPoint(lon, lat)

    # add ring to polygon
    grid_poly.AddGeometry(ring)
    if not grid_poly.IsValid():
        logging.debug(grid_poly)

    return grid_poly



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

    logging.debug('tile width: %s' % TileWidth)
    logging.debug('tile height: %s' % TileHeight)

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

    logging.warning('rows: %s' % rows)
    logging.warning('cols: %s' % cols)

    if rows < 1:
        rows = 1
    if cols < 1:
        cols = 1

    ############################################################

    for i in range(0,rows):
        TileX = TileX_left
        for j in range(0,cols):

            poly = create_grid_polygon(TileX, TileY, zoom, 3)
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

        poly = snap_ogr_geometries(poly, grid_geom, 0.000001)

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
                #if not intersection.IsValid():
                #    print(intersection)
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
                        #if not lo.IsValid():
                        #    print(lo)
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

        project_data_file = '{data_dir}/{project_id}/yes_maybe_results_{project_id}.json'.format(
            data_dir=data_dir,
            project_id=project_id
        )
        logging.warning(project_data_file)

        if not os.path.isfile(project_data_file):
            continue

        import json
        with open(project_data_file, 'r') as project_data_f:
            project_data = json.load(project_data_f)

            #ogr_geometry_collection = load_geom_from_geojson(project_data_file)
            project_data_dict[project_id] = {
                "yes_maybe_results": project_data
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


def check_neighbours(task_x, task_y, group_id):
    # potential neighbours
    neighbour_list = [
        [-2, -2], [-1, -2], [0, -2], [1, -2], [2, -2],
        [-2, -1], [-1, -1], [0, -1], [1, -1], [2, -1],
        [-2, 0], [-1, 0], [1, 0], [2, 0],
        [-2, 1], [-1, 1], [0, 1], [1, 1], [2, 1],
        [-2, 2], [-1, 2], [0, 2], [1, 2], [2, 2]
    ]

    # look for neighbours
    neighbours = []
    for i, j in neighbour_list:
        new_task_x = int(task_x) + i
        new_task_y = int(task_y) + j
        new_task_id = '18-{task_x}-{task_y}'.format(
            task_x=new_task_x,
            task_y=new_task_y
        )

        if new_task_id in yes_results_dict:
            yes_results_dict[new_task_id]['my_group_id'] = group_id
            neighbours.append(new_task_id)


def create_duplicates_dict():
    duplicated_groups = {}
    for task_id in yes_results_dict.keys():
        my_group_id = yes_results_dict[task_id]['my_group_id']
        # check for other results in the neighbourhood
        task_x = yes_results_dict[task_id]['task_x']
        task_y = yes_results_dict[task_id]['task_y']

        '''
        neighbour_list = [
            [-2, -2], [-1, -2], [0, -2], [1, -2], [2, -2],
            [-2, -1], [-1, -1], [0, -1], [1, -1], [2, -1],
            [-2, 0], [-1, 0], [1, 0], [2, 0],
            [-2, 1], [-1, 1], [0, 1], [1, 1], [2, 1],
            [-2, 2], [-1, 2], [0, 2], [1, 2], [2, 2]
        ]
        '''

        neighbour_list = [
             [-1, -2], [0, -2], [1, -2],
            [-2, -1], [-1, -1], [0, -1], [1, -1], [2, -1],
            [-2, 0], [-1, 0], [1, 0], [2, 0],
            [-2, 1], [-1, 1], [0, 1], [1, 1], [2, 1],
            [-1, 2], [0, 2], [1, 2]
        ]

        # look for neighbours
        neighbours = []
        for i, j in neighbour_list:
            new_task_x = int(task_x) + i
            new_task_y = int(task_y) + j
            new_task_id = '18-{task_x}-{task_y}'.format(
                task_x=new_task_x,
                task_y=new_task_y
            )

            if new_task_id in yes_results_dict:
                neighbours_group_id = yes_results_dict[new_task_id]['my_group_id']
                if neighbours_group_id != my_group_id:
                    # add the other group to duplicated groups dict
                    try:
                        duplicated_groups[my_group_id].add(neighbours_group_id)
                    except:
                        duplicated_groups[my_group_id] = set([neighbours_group_id])
                    # add my_group_id to other groupd_id in duplicated dict
                    try:
                        duplicated_groups[neighbours_group_id].add(my_group_id)
                    except:
                        duplicated_groups[neighbours_group_id] = set([my_group_id])

    return duplicated_groups


def remove_duplicates(duplicated_groups):
    for duplicated_group_id in sorted(duplicated_groups.keys(), reverse=True):
        #logging.warning('%s: %s' % (duplicated_group_id, list(duplicated_groups[duplicated_group_id])))
        my_duplicated_group_id = duplicated_group_id
        for other_group_id in duplicated_groups[duplicated_group_id]:
            if other_group_id < my_duplicated_group_id:
                my_duplicated_group_id = other_group_id

        for task_id in yes_results_dict.keys():
            if yes_results_dict[task_id]['my_group_id'] == duplicated_group_id:
                yes_results_dict[task_id]['my_group_id'] = my_duplicated_group_id


def get_utm_epsg(geometry):
    # get latitude of centroid
    extent = geometry.GetEnvelope()

    minX = extent[0]
    maxX = extent[1]
    # calc centroid

    center_lat = minX + (maxX - minX)
    utm_epsg = int((32600 + ((center_lat + 186) / 6)))
    utm = osr.SpatialReference()
    utm.ImportFromEPSG(utm_epsg)

    return utm


def transform_geometry(geometry, in_proj, out_proj):
    # transform geometry
    transform = osr.CoordinateTransformation(in_proj, out_proj)
    geometry.Transform(transform)
    logging.debug('transformed geometry')
    return geometry


def create_group_geom_for_small_groups(group_data):
    result_geom_collection = ogr.Geometry(ogr.wkbMultiPolygon)
    group_geom = ogr.Geometry(ogr.wkbMultiPolygon)
    for result, data in group_data.items():
        result_geom = ogr.CreateGeometryFromWkt(data['wkt'])
        result_geom_collection.AddGeometry(result_geom)

    # wgs and utm
    wgs = osr.SpatialReference()
    wgs.ImportFromEPSG(4326)
    utm = get_utm_epsg(result_geom_collection)

    # transform geometry
    utm_geometry = transform_geometry(result_geom_collection, wgs, utm)

    delaunay_select = ogr.Geometry(ogr.wkbMultiPolygon)
    delaunay_geom_collection = utm_geometry.DelaunayTriangulation()
    for geom in delaunay_geom_collection:
        # Select only valid triangles
        area = float(geom.GetArea())
        perimeter = geom.Boundary().Length()
        # if (area <= 40000.0) & (perimeter <= 800.0):
        if (area <= 45000.0) & (perimeter <= 950.0):
            delaunay_select.AddGeometry(geom)
            continue
    logging.debug('selected valid triangles')
    # transform geometries
    wgs_delaunay_select = transform_geometry(delaunay_select, utm, wgs)

    group_geom = wgs_delaunay_select.UnionCascaded()
    return group_geom


def split_up_bigger_groups(group_id, group_data):
    logging.warning('the group (%s) has %s members' % (group_id, len(group_data)))

    group_threshold = 9

    targeted_group_number = math.floor(len(group_data)/group_threshold) + 1
    logging.warning(targeted_group_number)

    smaller_groups = ''

    return smaller_groups



########################################################################################################################


def create_hot_tm_tasks(project_data_dict):


    final_project_data_dict = {}


    for project_id, project_data in project_data_dict.items():

        groups_dict = {}

        # create output geometry collections
        final_coll = ogr.Geometry(ogr.wkbGeometryCollection)

        # create a dictionary with the results
        global yes_results_dict
        yes_results_dict = {}
        for result in project_data['yes_maybe_results']:
            yes_results_dict[result['id']] = result
        logging.warning('create results dictionary. there are %s results.' % len(yes_results_dict))

        highest_group_id = 0
        # test for neighbors and set groups id
        counter = 0

        for task_id in sorted(yes_results_dict.keys()):
            logging.warning(task_id)
            counter += 1
            logging.warning(counter)
            try:
                # this task has already a group id, great.
                group_id = yes_results_dict[task_id]['my_group_id']
            except:
                group_id = highest_group_id + 1
                highest_group_id += 1
                yes_results_dict[task_id]['my_group_id'] = group_id
                logging.warning('created new group id')

            logging.warning('group id: %s' % group_id)

            # check for other results in the neighbourhood
            task_x = yes_results_dict[task_id]['task_x']
            task_y = yes_results_dict[task_id]['task_y']

            neighbours = check_neighbours(task_x, task_y, group_id)


        # check if some tasks have different groups from their neighbours
        duplicates_dict = create_duplicates_dict()
        while len(duplicates_dict) > 0:
            remove_duplicates(duplicates_dict)
            duplicates_dict = create_duplicates_dict()
            logging.warning(len(duplicates_dict))

        grouped_results_dict = {}
        for task_id in yes_results_dict.keys():
            group_id = yes_results_dict[task_id]['my_group_id']
            try:
                grouped_results_dict[group_id][task_id] = yes_results_dict[task_id]
            except:
                grouped_results_dict[group_id] = {}
                grouped_results_dict[group_id][task_id] = yes_results_dict[task_id]

        logging.warning(len(grouped_results_dict))


        # create geojson for groups
        # create geojson file for testing with output
        # set driver for shapefile or geojson
        output_type = 'geojson'
        outfile = 'yes_maybe_groups.geojson'
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
        group_id_field = ogr.FieldDefn('group_id', ogr.OFTInteger)
        layer.CreateField(group_id_field)

        # go through all groups
        big_groups_counter = 0
        for group_id in grouped_results_dict.keys():

            if len(grouped_results_dict[group_id]) < 1:
                logging.warning('empty group?')
                logging.warning(grouped_results_dict[group_id])
            elif len(grouped_results_dict[group_id]) < 9:
                #logging.warning('this is a small group: %s' % group_id)
                group_data = grouped_results_dict[group_id]
                group_geom = create_group_geom_for_small_groups(group_data)
                grouped_results_dict[group_id]['group_geom'] = group_geom

                # init feature
                featureDefn = layer.GetLayerDefn()
                feature = ogr.Feature(featureDefn)
                # create polygon from wkt and set geometry
                feature.SetGeometry(group_geom)
                # set other attributes
                feature.SetField('group_id', group_id)
                # add feature to layer
                layer.CreateFeature(feature)


            else:
                big_groups_counter += 1
                group_data = grouped_results_dict[group_id]
                split_up_bigger_groups(group_id, group_data)
                #logging.warning('this is a big group: %s' % group_id)

        logging.warning(big_groups_counter)
        layer = None
        dataSoure = None
        logging.warning('created outfile: %s.' % outfile)


        # replace the duplicated groups
        #logging.warning(duplicated_groups)
        '''
        for task_id in yes_results_dict.keys():
            my_group_id = yes_results_dict[task_id]['my_group_id']

            # are there other group ids?
            if my_group_id in duplicated_groups:
                for other_group_id in duplicated_groups[my_group_id]:
                    if other_group_id < my_group_id:
                        my_group_id = other_group_id

                #replace my group id
        '''







        # create geojson file for testing with output
        # set driver for shapefile or geojson
        output_type = 'geojson'
        outfile = 'yes_maybe_grouped.geojson'
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
        group_id_field = ogr.FieldDefn('my_group_id', ogr.OFTInteger)
        layer.CreateField(group_id_field)

        counter = 0
        for task_id in yes_results_dict.keys():
            counter += 1
            # init feature
            featureDefn = layer.GetLayerDefn()
            feature = ogr.Feature(featureDefn)
            # create polygon from wkt and set geometry
            geom = ogr.CreateGeometryFromWkt(yes_results_dict[task_id]['wkt'])
            feature.SetGeometry(geom)
            # set other attributes
            feature.SetField('id', task_id)
            feature.SetField('my_group_id', yes_results_dict[task_id]['my_group_id'])
            # add feature to layer
            layer.CreateFeature(feature)

        layer = None
        dataSoure = None
        logging.warning('created outifle: %s.' % outfile)

    import sys
    sys.exit()
    #return final_project_data_dict


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
