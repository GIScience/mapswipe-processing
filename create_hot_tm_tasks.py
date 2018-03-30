#!/bin/python
# -*- coding: UTF-8 -*-
# Author: B. Herfort, 2016
# Modified by: M. Reinmuth
########################################################################################################################

#import libs

import sys
import os  # Require module os for file/directory handling
import logging
from distutils.dir_util import mkpath
import ogr
import osr
from queue import Queue
import threading
from tile_functions import *

import argparse
# define arguments that can be passed by the user
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-p', '--projects', nargs='+', required=None, default=None, type=int,
                    help='project id of the project to process. You can add multiple project ids.')
parser.add_argument('-d', '--data_dir', required=True, type=str,
                    help='data location')
parser.add_argument('-t', '--output_type', nargs='?', default='geojson',choices=['geojson', 'shp'])
parser.add_argument('-g', '--group_size', required=None, default=15, type=int,
                    help='The maximum number of results that will be merged into one mapping task.')
parser.add_argument('-n_shape', '--neighbourhood_shape', nargs='?', default='rectangle', choices=['star', 'rectangle'],
                    help='The search neighbourhood shape in tiles which will be used to group results into tasks')
parser.add_argument('-n_size', '--neighbourhood_size', required=None, default=5, type=int,
                    help='The search neighbourhood size in tiles which will be used to group results into tasks')

########################################################################################################################


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


def create_geofile(final_groups_dict, outfile, output_type):
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
    field_id = ogr.FieldDefn('group_id', ogr.OFTInteger)
    layer.CreateField(field_id)

    if len(final_groups_dict) < 1:
        logging.warning('there are no geometries to save')
    else:
        for group_id in final_groups_dict.keys():
            group_data = final_groups_dict[group_id]
            group_geom = create_group_geom(group_data)
            final_groups_dict[group_id]['group_geom'] = group_geom
            # init feature
            featureDefn = layer.GetLayerDefn()
            feature = ogr.Feature(featureDefn)
            # create polygon from wkt and set geometry
            feature.SetGeometry(group_geom)
            # set other attributes
            feature.SetField('group_id', group_id)
            # add feature to layer
            layer.CreateFeature(feature)

    layer = None
    dataSoure = None
    logging.warning('created outfile: %s.' % outfile)


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


def check_list_sum(x, range_val):
    item_sum = abs(x[0]) + abs(x[1])
    if item_sum <= range_val:
        return True
    else:
        return False


def get_neighbour_list(neighbourhood_shape, neighbourhood_size):

    neighbour_list = []
    range_val = int(neighbourhood_size/2)
    for i in range(-range_val, range_val + 1):
        for j in range(-range_val, range_val + 1):
            if i == 0 and j == 0:
                pass
            else:
                neighbour_list.append([i, j])

    if neighbourhood_shape == 'star':
        neighbour_list = [x for x in neighbour_list if check_list_sum(x, range_val)]

    return neighbour_list


def check_neighbours(task_x, task_y, group_id):

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


        # look for neighbours
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
        logging.debug('%s: %s' % (duplicated_group_id, list(duplicated_groups[duplicated_group_id])))
        my_duplicated_group_id = duplicated_group_id
        for other_group_id in duplicated_groups[duplicated_group_id]:
            if other_group_id < my_duplicated_group_id:
                my_duplicated_group_id = other_group_id

        for task_id in yes_results_dict.keys():
            if yes_results_dict[task_id]['my_group_id'] == duplicated_group_id:
                yes_results_dict[task_id]['my_group_id'] = my_duplicated_group_id


def create_group_geom(group_data):
    result_geom_collection = ogr.Geometry(ogr.wkbMultiPolygon)
    for result, data in group_data.items():
        result_geom = ogr.CreateGeometryFromWkt(data['wkt'])
        result_geom_collection.AddGeometry(result_geom)

    group_geom = result_geom_collection.ConvexHull()
    return group_geom


def split_groups(q):
    while not q.empty():
        group_id, group_data, group_size = q.get()
        logging.debug('the group (%s) has %s members' % (group_id, len(group_data)))

        # find min x, and min y
        x_list = []
        y_list = []

        for result, data in group_data.items():
            x_list.append(int(data['task_x']))
            y_list.append(int(data['task_y']))

        min_x = min(x_list)
        max_x = max(x_list)
        x_width = max_x - min_x

        min_y = min(y_list)
        max_y = max(y_list)
        y_width = max_y - min_y

        new_grouped_data = {
            'a': {},
            'b': {}
        }

        if x_width >= y_width:
            # first split vertically
            for result, data in group_data.items():
                # result is in first segment
                if int(data['task_x']) < (min_x + (x_width/2)):
                    new_grouped_data['a'][result] = data
                else:
                    new_grouped_data['b'][result] = data
        else:
            # first split horizontally
            for result, data in group_data.items():
                # result is in first segment
                if int(data['task_y']) < (min_y + (y_width / 2)):
                    new_grouped_data['a'][result] = data
                else:
                    new_grouped_data['b'][result] = data

        for k in ['a', 'b']:
            logging.debug('there are %s results in %s' % (len(new_grouped_data[k]), k))

            for result, data in new_grouped_data[k].items():
                x_list.append(int(data['task_x']))
                y_list.append(int(data['task_y']))

            min_x = min(x_list)
            max_x = max(x_list)
            x_width = max_x - min_x

            min_y = min(y_list)
            max_y = max(y_list)
            y_width = max_y - min_y


            if len(new_grouped_data[k]) < group_size:

                # add this check to avoid large groups groups with few items
                if x_width * y_width > 2 * (my_neighbourhood_size * my_neighbourhood_size):
                    q.put([group_id, new_grouped_data[k], group_size])
                else:
                    split_groups_list.append(new_grouped_data[k])
                    logging.debug('add "a" to split_groups_dict')
            else:
                # add this group to a queue
                q.put([group_id, new_grouped_data[k], group_size])

        q.task_done()


def create_final_groups_dict(project_data, group_size, neighbourhood_shape, neighbourhood_size):

    # final groups dict will store the groups that are exported
    final_groups_dict = {}
    highest_group_id = 0

    # create a dictionary with all results
    global yes_results_dict
    yes_results_dict = {}
    for result in project_data['yes_maybe_results']:
        yes_results_dict[result['id']] = result
    logging.warning('created results dictionary. there are %s results.' % len(yes_results_dict))
    if len(yes_results_dict) < 1:
        return final_groups_dict

    global neighbour_list
    global my_neighbourhood_size
    my_neighbourhood_size = neighbourhood_size

    neighbour_list = get_neighbour_list(neighbourhood_shape, neighbourhood_size)
    logging.warning('got neighbour list. neighbourhood_shape: %s, neighbourhood_size: %s' % (neighbourhood_shape, neighbourhood_size))

    global split_groups_list
    split_groups_list = []



    # test for neighbors and set groups id
    for task_id in sorted(yes_results_dict.keys()):
        try:
            # this task has already a group id, great.
            group_id = yes_results_dict[task_id]['my_group_id']
        except:
            group_id = highest_group_id + 1
            highest_group_id += 1
            yes_results_dict[task_id]['my_group_id'] = group_id
            logging.debug('created new group id')
        logging.debug('group id: %s' % group_id)

        # check for other results in the neighbourhood
        task_x = yes_results_dict[task_id]['task_x']
        task_y = yes_results_dict[task_id]['task_y']

        check_neighbours(task_x, task_y, group_id)

    logging.warning('added group ids to yes maybe results dict')

    # check if some tasks have different groups from their neighbours
    duplicates_dict = create_duplicates_dict()
    while len(duplicates_dict) > 0:
        remove_duplicates(duplicates_dict)
        duplicates_dict = create_duplicates_dict()
        logging.debug('there are %s duplicated groups' % len(duplicates_dict))

    logging.warning('removed all duplicated group ids in yes maybe results dict')

    grouped_results_dict = {}
    for task_id in yes_results_dict.keys():
        group_id = yes_results_dict[task_id]['my_group_id']
        try:
            grouped_results_dict[group_id][task_id] = yes_results_dict[task_id]
        except:
            grouped_results_dict[group_id] = {}
            grouped_results_dict[group_id][task_id] = yes_results_dict[task_id]

    logging.warning('created dict item for each group')

    # reset highest group id since we merged several groups
    highest_group_id = max(grouped_results_dict)
    logging.debug('new highest group id: %s' % highest_group_id)

    q = Queue(maxsize=0)
    num_threads = 1

    for group_id in grouped_results_dict.keys():

        if len(grouped_results_dict[group_id]) < group_size:
            final_groups_dict[group_id] = grouped_results_dict[group_id]
        else:
            group_data = grouped_results_dict[group_id]
            # add this group to the queue
            q.put([group_id, group_data, group_size])

    logging.warning('added groups to queue.')

    for i in range(num_threads):
        worker = threading.Thread(
            target=split_groups,
            args=(q,))
        worker.start()

    q.join()
    logging.warning('split all groups.')

    logging.debug('there are %s split groups' % len(split_groups_list))

    # add the split groups to the final groups dict
    for group_data in split_groups_list:
        new_group_id = highest_group_id + 1
        highest_group_id += 1
        final_groups_dict[new_group_id] = group_data

    logging.warning('created %s groups.' % len(final_groups_dict))
    return final_groups_dict


########################################################################################################################


def create_hot_tm_tasks(project_data_dict, group_size, neighbourhood_shape, neighbourhood_size):

    final_project_data_dict = {}
    for project_id, project_data in project_data_dict.items():

        final_groups_dict = create_final_groups_dict(project_data, group_size, neighbourhood_shape, neighbourhood_size)
        final_project_data_dict[project_id] = final_groups_dict

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
    final_project_data_dict = create_hot_tm_tasks(project_data_dict, args.group_size, args.neighbourhood_shape, args.neighbourhood_size)
    save_project_data(final_project_data_dict, args.data_dir, args.output_type)
    sys.exit()
