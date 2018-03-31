#!/bin/python
# -*- coding: UTF-8 -*-
# Author: M. Dollinger, B. Herfort, M. Reinmuth 2018
########################################################################################################################

import logging
import os
from distutils.dir_util import mkpath
import ogr, osr
import json
import argparse
# define arguments that can be passed by the user
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-p', '--projects', nargs='+', required=None, default=None, type=int,
                    help='project id of the project to process. You can add multiple project ids.')
parser.add_argument('-d', '--data_dir', required=True, type=str,
                    help='data location')
parser.add_argument('-t', '--output_type', nargs='?', default='geojson',choices=['geojson', 'shp'])


########################################################################################################################
def create_project_data_dict(project_id_list, data_dir):

    project_data_dict = {}

    for project_id in project_id_list:

        project_data_file = '{data_dir}/{project_id}/results_{project_id}.json'.format(
            data_dir=data_dir,
            project_id=project_id
        )
        if not os.path.isfile(project_data_file):
            continue

        project_data = json.load(open(project_data_file))
        project_data_dict[project_id] = project_data

    return project_data_dict


def yes_maybe_condition_true(x):
    if x['yes_count'] > 1:
        return True
    elif x['yes_count'] > 1 and x['yes_count'] >= x['bad_imagery_count']:
        return True
    elif x['maybe_count'] > 1 and x['maybe_count'] >= x['bad_imagery_count']:
        return True
    elif x['yes_count'] >= 1 and x['maybe_count'] >= 1 and ((x['yes_count'] + x['maybe_count']) >= x['bad_imagery_count']):
        return True
    else:
        return False


def bad_image_condition_true(x):
    if x['bad_imagery_count'] > (x['yes_count'] + x['maybe_count']):
        return True
    else:
        return False


def filter_project_data(project_data, object_type):

    if object_type == 'yes_maybe':
        filtered_project_data = [x for x in project_data if yes_maybe_condition_true(x)]
    elif object_type == 'bad_image':
        filtered_project_data = [x for x in project_data if bad_image_condition_true(x)]

    logging.warning('filtered project data, input: %s items, output: %s items' % (len(project_data), len(filtered_project_data)))
    return filtered_project_data


def multipolygon_from_project_data(project_data):

    multipolygon_geometry = ogr.Geometry(ogr.wkbMultiPolygon)
    for item in project_data:
        polygon = ogr.CreateGeometryFromWkt(item['wkt'])
        multipolygon_geometry.AddGeometry(polygon)

    return multipolygon_geometry


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
    logging.warning('transformed geometry')
    return geometry


def dissolve_project_data(multipolygon_geometry):
    dissolved_geometry = multipolygon_geometry.UnionCascaded()
    return dissolved_geometry


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
    if not geometries:
        logging.warning('there are no geometries to save')
    else:
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


def save_dissolved_project_data(dissolved_project_data_dict, output_path, output_type):

    for project_id, vals in dissolved_project_data_dict.items():
        # save yes maybe
        final_output_path = '{output_path}/{project_id}'.format(
            output_path=output_path,
            project_id=project_id
        )

        # check if a data folder already exists
        if not os.path.exists(final_output_path):
            mkpath(final_output_path)
            logging.warning('Added the output folder')

        outfile = '{final_output_path}/yes_maybe_{project_id}.{output_type}'.format(
            final_output_path=final_output_path,
            project_id=project_id,
            output_type=output_type

        )
        create_geofile(dissolved_project_data_dict[project_id]['yes_maybe'], outfile, output_type)

        # save bad image
        outfile = '{final_output_path}/bad_image_{project_id}.{output_type}'.format(
            final_output_path=final_output_path,
            project_id=project_id,
            output_type=output_type

        )
        create_geofile(dissolved_project_data_dict[project_id]['bad_image'], outfile, output_type)

        # save yes maybe results
        outfile = '{final_output_path}/yes_maybe_results_{project_id}.json'.format(
            final_output_path=final_output_path,
            project_id=project_id,
            output_type=output_type

        )
        with open(outfile, 'w') as out_file:
            json.dump(dissolved_project_data_dict[project_id]['yes_maybe_results'], out_file)
        logging.warning('created outfile: %s' % outfile)



########################################################################################################################
def select_and_dissolve(project_data_dict):

    dissolved_project_data_dict = {}

    for project_id, project_data in project_data_dict.items():
        logging.warning('project %s , start select and aggregate' % project_id)

        # filter yes and maybe
        filtered_project_data = filter_project_data(project_data, 'yes_maybe')
        multipolygon_geometry = multipolygon_from_project_data(filtered_project_data)
        dissolved_yes_maybe_geometry = dissolve_project_data(multipolygon_geometry)

        # filter bad image
        filtered_project_data_bad = filter_project_data(project_data, 'bad_image')
        multipolygon_geometry = multipolygon_from_project_data(filtered_project_data_bad)
        dissolved_bad_image_geometry = dissolve_project_data(multipolygon_geometry)

        # add to dictionary
        dissolved_project_data_dict[project_id] = {
            "yes_maybe": dissolved_yes_maybe_geometry,
            "bad_image": dissolved_bad_image_geometry,
            "yes_maybe_results": filtered_project_data
        }

    return dissolved_project_data_dict


########################################################################################################################
if __name__ == '__main__':
    logging.basicConfig(filename='select_and_dissolve.log',
                        level=logging.WARNING,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M:%S',
                        filemode='a'
                        )

    logging.getLogger().addHandler(logging.StreamHandler())

    try:
        args = parser.parse_args()
    except:
        print('have a look at the input arguments, something went wrong there.')

    project_data_dict = create_project_data_dict(args.projects, args.data_dir)
    dissolved_project_data_dict = select_and_dissolve(project_data_dict)
    save_dissolved_project_data(dissolved_project_data_dict, args.data_dir, args.output_type)




