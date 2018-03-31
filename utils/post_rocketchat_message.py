#!/bin/python3
##############

########################################################################################################################
#
# You can find more information on:
# https://github.com/jadolg/rocketchat_API
#
# Please provide a config file as input
#
# {
# "rocketchat": {
#   "username": "your_username",
#   "password": "your_password",
#   "server_url": "your_server_url",
#   "channel": "your_channel"
#   }
# }
#
########################################################################################################################

import sys
from rocketchat_API.rocketchat import RocketChat
import json
import logging
import argparse

parser = argparse.ArgumentParser(description='get info from you.')
parser.add_argument('-c', '--config_file', required=False, default='config.conf', type=str, help='Please provide the path to config file')
parser.add_argument('-m', '--message', required=False, default='Hello World', type=str, help='What would you like to post?')

########################################################################################################################


def get_config(config_file):
    # read config from config.conf file
    # returns a dictionary
    try:
        with open(config_file) as conf_file:
            data = json.load(conf_file)

            rocketchat_config = {
                "server_url": data["rocketchat"]["server_url"],
                "username": data["rocketchat"]["username"],
                "password": data["rocketchat"]["password"],
                "channel": data["rocketchat"]["channel"]
            }

            #logging.info("got info from conf file")
            return rocketchat_config
    except:
        #logging.warning("could not read conf file")
        sys.exit(1)


def post_rocketchat_message(config_file, msg):

    # get config from file
    r_cfg = get_config(config_file)

    # Authentification
    rocket = RocketChat(r_cfg['username'], r_cfg['password'], server_url=r_cfg['server_url'])

    # post message
    r = rocket.chat_post_message(msg, channel=r_cfg['channel'])
    logging.info("response status code: %s" % r.status_code)


########################################################################################################################
if __name__ == "__main__":
    try:
        args = parser.parse_args()
    except:
        print('have a look at the input arguments, something went wrong there.')

    post_rocketchat_message(args.config_file, args.message)