#!/bin/python
# -*- coding: UTF-8 -*-
# Author: M. Dollinger, B. Herfort, M. Reinmuth 2018
########################################################################################################################

import os
import ogr, osr
from distutils.dir_util import mkpath
import json
import argparse
import requests
import logging
import csv
from tile_functions import geometry_from_tile_coords


# define arguments that can be passed by the user
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-p', '--projects', nargs='+', required=None, default=None, type=int,
                    help='project id of the project to process. You can add multiple project ids.')
parser.add_argument('-o', '--output_path', required=True, type=str,
                    help='output location')
parser.add_argument('-t', '--output_type', nargs='?', default='geojson',choices=['geojson', 'shp', 'csv', 'json'])

########################################################################################################################


def download_project_data(project_id):
    # get project information, loop through every project
    project_url = 'http://api.mapswipe.org/projects/{project_id}.json'.format(
        project_id=project_id
    )

    # get data for the project
    try:
        r = requests.get(project_url)
        logging.warning('project: %s , Data downloaded' % project_id)
    except:
        logging.warning('project: %s , api is currently not available. Please try again later.' % project_id)
        return False
    try:
        project_data_json = json.loads(r.text)
        logging.warning('project: %s , parsed data as json' % project_id)
        return project_data_json
    except:
        logging.warning('project: %s , api is available, but theres an error parsing the json information. Please try again later.' % project_id)
        return False


def check_project_data(project_data, project_id):

    if not project_data:
        logging.warning('Project %s, no data downloaded or not available.' % project_id)
    elif len(project_data) < 12:
        logging.warning('Project %s misses critical data in api, please contact the administrator of mapswipe data infrastructure or try another project' % project_id)
        return False
    else:
        logging.warning('Project %s, is valid and has all attributes.' % project_id)
        return True


def add_wkt_geometry(project_data, project_id):

    for item in project_data:
        item[u'wkt'] = geometry_from_tile_coords(int(item[u'task_x']), int(item[u'task_y']), int(item[u'task_z']))

    logging.warning('Project %s, added wkt geometry.' % project_id)
    return project_data


def save_downloaded_project_data(project_data_dict, output_path, output_type):

    for project_id, project_data in project_data_dict.items():
        final_output_path = '{output_path}/{project_id}'.format(
            output_path=output_path,
            project_id=project_id
        )

        outfile = '{final_output_path}/results_{project_id}.{output_type}'.format(
            final_output_path=final_output_path,
            project_id=project_id,
            output_type=output_type
        )

        # check if a data folder already exists
        if not os.path.exists(final_output_path):
            mkpath(final_output_path)
            logging.warning('Added the output folder')

        if output_type == 'geojson':
            create_geofile(project_data, outfile, 'geojson')
        elif output_type == 'shp':
            create_geofile(project_data, outfile, 'shp')
        elif output_type == 'csv':
            create_csv(project_data, outfile)
        elif output_type == 'json':
            create_json(project_data, outfile)


def create_json(project_data, outfile):
    with open(outfile, 'w') as fileJson:
        json.dump(project_data, fileJson)
        logging.warning('created outifle: %s.' % outfile)


def create_csv(project_data, outfile):
    with open(outfile, 'w') as fileCsv:
        fieldnames = [u'id', u'project', u'task_x', u'task_y', u'task_z', u'decision',
                      u'yes_count', u'maybe_count', u'bad_imagery_count', 'wkt']
        # set extrasaction to ignore to ignore additional fields in dict
        writer = csv.DictWriter(fileCsv, fieldnames=fieldnames,  extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        for item in project_data:
            writer.writerow(item)
        logging.warning('created outifle: %s.' % outfile)


def create_geofile(project_data, outfile, output_type):
    # driver for Shapefiles
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
    field_project = ogr.FieldDefn('project_id', ogr.OFTInteger)
    layer.CreateField(field_project)
    field_task_x = ogr.FieldDefn('task_x', ogr.OFTInteger)
    layer.CreateField(field_task_x)
    field_task_y = ogr.FieldDefn('task_y', ogr.OFTInteger)
    layer.CreateField(field_task_y)
    field_task_z = ogr.FieldDefn('task_z', ogr.OFTInteger)
    layer.CreateField(field_task_z)
    field_decision = ogr.FieldDefn('decision', ogr.OFTReal)
    layer.CreateField(field_decision)
    field_yes_count = ogr.FieldDefn('yes', ogr.OFTInteger)
    layer.CreateField(field_yes_count)
    field_maybe_count = ogr.FieldDefn('maybe', ogr.OFTInteger)
    layer.CreateField(field_maybe_count)
    field_bad_imagery_count = ogr.FieldDefn('bad_image', ogr.OFTInteger)
    layer.CreateField(field_bad_imagery_count)

    for item in project_data:
        # init feature
        featureDefn = layer.GetLayerDefn()
        feature = ogr.Feature(featureDefn)
        # create polygon from wkt and set geometry
        polygon = ogr.CreateGeometryFromWkt(item['wkt'])
        feature.SetGeometry(polygon)
        # set other attributes
        feature.SetField('id', item['id'])
        feature.SetField('project_id', item['project'])
        feature.SetField('task_x', item['task_x'])
        feature.SetField('task_y', item['task_y'])
        feature.SetField('task_z', item['task_z'])
        feature.SetField('decision', item['decision'])
        feature.SetField('yes', item['yes_count'])
        feature.SetField('maybe', item['maybe_count'])
        feature.SetField('bad_image', item['bad_imagery_count'])
        # add feature to layer
        layer.CreateFeature(feature)

    layer = None
    dataSoure = None
    logging.warning('created outifle: %s.' % outfile)

########################################################################################################################


def download_data(project_id_list):

    logging.basicConfig(filename='download_data.log',
                        level=logging.WARNING,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M:%S',
                        filemode='a'
                        )

    project_data_dict = {}

    for project_id in project_id_list:
        # download json file from api.mapswipe.org
        project_data = download_project_data(project_id)

        if not check_project_data(project_data, project_id):
            continue

        project_data = add_wkt_geometry(project_data, project_id)
        project_data_dict[project_id] = project_data

    return project_data_dict

########################################################################################################################
if __name__ == '__main__':
    try:
        args = parser.parse_args()
    except:
        print('have a look at the input arguments, something went wrong there.')

    logging.getLogger().addHandler(logging.StreamHandler())
    project_data_dict = download_data(args.projects)
    save_downloaded_project_data(project_data_dict, args.output_path, args.output_type)

