#!/bin/python
# -*- coding: UTF-8 -*-
# Author: M. Dollinger, B. Herfort, M. Reinmuth 2018
########################################################################################################################

from download_data import download_data
from download_data import save_downloaded_project_data
from create_hot_tm_tasks import create_hot_tm_tasks
from create_hot_tm_tasks import save_project_data
from select_and_dissolve import select_and_dissolve
from select_and_dissolve import save_dissolved_project_data
import argparse
import logging
import sys

# define arguments that can be passed by the user
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-p', '--projects', nargs='+', required=None, default=None, type=int,
                    help='project id of the project to process. You can add multiple project ids.')
parser.add_argument('-o', '--output_path', required=True, type=str,
                    help='output location')
parser.add_argument('-t', '--output_type', nargs='?', default='geojson', choices=['geojson', 'shp'])
parser.add_argument('-mo', '--modus', nargs='?', default='hot_tm',choices=['hot_tm', 'download', 'dissolve', 'all'])
########################################################################################################################

def run_mapswipe_tools(project_id_list, output_path, output_type, modus):
    logging.basicConfig(filename='run_mapswipe_tools.log',
                        level=logging.WARNING,
                        format='%(asctime)s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M:%S',
                        filemode='a'
                        )
    logging.getLogger().addHandler(logging.StreamHandler())

    project_data_dict = download_data(project_id_list)
    if modus == 'download':
        # save output as specified
        save_downloaded_project_data(project_data_dict, output_path, output_type)
        sys.exit('stop after download')

    dissolved_project_data_dict = select_and_dissolve(project_data_dict)
    if modus == 'dissolve':
        # save output as specified
        save_dissolved_project_data(dissolved_project_data_dict, output_path, output_type)
        sys.exit('stop after dissolve')

    final_project_data_dict = create_hot_tm_tasks(dissolved_project_data_dict)
    if modus == 'hot_tm':
        save_project_data(final_project_data_dict, output_path, 'geojson')
        sys.exit('stop after tasks created')

    if modus == 'all':
        save_downloaded_project_data(project_data_dict, output_path, output_type)
        save_dissolved_project_data(dissolved_project_data_dict, output_path, output_type)
        save_project_data(final_project_data_dict, output_path, output_type)



########################################################################################################################
if __name__ == '__main__':
    try:
        args = parser.parse_args()
    except:
        print('have a look at the input arguments, something went wrong there.')

    run_mapswipe_tools(args.projects, args.output_path, args.output_type, args.modus)
