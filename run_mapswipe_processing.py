#!/bin/python
# -*- coding: UTF-8 -*-
# Author: M. Dollinger, B. Herfort, M. Reinmuth 2018
########################################################################################################################

import os
from download_data import download_data
from download_data import save_downloaded_project_data
from create_hot_tm_tasks import create_hot_tm_tasks
from create_hot_tm_tasks import save_project_data
from select_and_dissolve import select_and_dissolve
from select_and_dissolve import save_dissolved_project_data
import argparse
import logging
import sys
import json
import requests

# define arguments that can be passed by the user
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-p', '--projects', nargs='+', required=None, default=None, type=int,
                    help='project id of the project to process. You can add multiple project ids.')
parser.add_argument('-a', '--all_projects', dest='all_projects', action='store_true',
                    help='flag to download all projects which changed since last download.')
parser.add_argument('-o', '--output_path', required=None, type=str, default='data',
                    help='output location')
parser.add_argument('-t', '--output_type', nargs='?', default='geojson', choices=['geojson', 'shp'])
parser.add_argument('-mo', '--modus', nargs='?', default='hot_tm',choices=['hot_tm', 'download', 'dissolve', 'all'])
########################################################################################################################


def save_project_file(filename, project_data):
    # save project info to json file
    with open(filename, 'w') as project_data_file:
        json.dump(project_data, project_data_file)
    logging.warning('wrote project data to file: %s' % filename)


def get_new_project_data():
    url = 'http://api.mapswipe.org/projects.json'
    r = requests.get(url)
    project_data = json.loads(r.text)
    logging.warning('got project data from mapswipe api.')
    return project_data


def get_old_project_data(filename):
    if os.path.isfile(filename):
        with open(filename, 'r') as project_data_file:
            project_data = json.load(project_data_file)
        logging.warning('got "old" project data local file')
        return project_data
    else:
        return False


def get_updated_projects(old_project_data, new_project_data):
    project_id_list = []

    for project_id, data in new_project_data.items():
        if len(data) < 12:
            continue
        # test if something changed
        elif project_id not in old_project_data.keys():
            project_id_list.append(project_id)
        elif data['progress'] > old_project_data[project_id]['progress']:
            project_id_list.append(project_id)
        elif data['contributors'] > old_project_data[project_id]['contributors']:
            project_id_list.append(project_id)
        else:
            pass
    logging.warning('returned list with updated projects: %s' % project_id_list)
    return project_id_list


def run_mapswipe_processing(project_id_list, output_path, output_type, modus, all_projects):
    logging.basicConfig(filename='run_mapswipe_tools.log',
                        level=logging.WARNING,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M:%S',
                        filemode='a'
                        )
    logging.getLogger().addHandler(logging.StreamHandler())

    if all_projects:
        # the users wants to download all projects
        # check for existing projects.json file
        project_data_filename = 'projects.json'
        old_project_data = get_old_project_data(project_data_filename)
        if not old_project_data:
            # get new project data
            project_data = get_new_project_data()
            project_id_list = list(project_data.keys())
        else:
            new_project_data = get_new_project_data()
            project_id_list = get_updated_projects(old_project_data, new_project_data)


    project_data_dict = download_data(project_id_list)
    if modus == 'download':
        # save output as specified
        save_downloaded_project_data(project_data_dict, output_path, output_type)
        if all_projects:
            save_project_file(project_data_filename, new_project_data)
        sys.exit('stop after download')

    dissolved_project_data_dict = select_and_dissolve(project_data_dict)
    if modus == 'dissolve':
        # save output as specified
        save_dissolved_project_data(dissolved_project_data_dict, output_path, output_type)
        if all_projects:
            save_project_file(project_data_filename, new_project_data)
        sys.exit('stop after dissolve')

    final_project_data_dict = create_hot_tm_tasks(dissolved_project_data_dict)
    if modus == 'hot_tm':
        save_project_data(final_project_data_dict, output_path, 'geojson')
        if all_projects:
            save_project_file(project_data_filename, new_project_data)
        sys.exit('stop after tasks created')

    if modus == 'all':
        save_downloaded_project_data(project_data_dict, output_path, output_type)
        save_dissolved_project_data(dissolved_project_data_dict, output_path, output_type)
        save_project_data(final_project_data_dict, output_path, output_type)
        if all_projects:
            save_project_file(project_data_filename, new_project_data)



########################################################################################################################
if __name__ == '__main__':
    try:
        args = parser.parse_args()
    except:
        print('have a look at the input arguments, something went wrong there.')

    run_mapswipe_processing(args.projects, args.output_path, args.output_type, args.modus, args.all_projects)
