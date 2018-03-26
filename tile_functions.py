#!/bin/python
# -*- coding: UTF-8 -*-
# Authors: B. Herfort, M. Reinmuth, M. Dollinger, 2018
########################################################################################################################
# import libs

import math # calculations etc
import ogr

########################################################################################################################
# create tile geometries

class Tile:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y


class Point:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y


def lat_long_zoom_to_pixel_coords(lat, lon, zoom):
    p = Point()
    sinLat = math.sin(lat * math.pi/180.0)
    x = ((lon + 180) / 360) * 256 * math.pow(2,zoom)
    y = (0.5 - math.log((1 + sinLat) / (1 - sinLat)) /
          (4 * math.pi)) * 256 * math.pow(2,zoom)
    p.x = int(math.floor(x))
    p.y = int(math.floor(y))
    #print "\nThe pixel coordinates are x = {} and y = {}".format(p.x, p.y)
    return p


def pixel_coords_zoom_to_lat_lon(PixelX, PixelY, zoom):
    # Calculate lat, lon of upper left corner of tile
    p = Point()
    MapSize = 256 * math.pow(2, zoom)
    x = (PixelX / MapSize) - 0.5
    y = 0.5 - (PixelY / MapSize)
    p.x = round((360 * x), 8)
    p.y = round((90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi), 8)
    # always remember lon --> x, lat --> y !!!
    return p


def pixel_coords_to_tile_address(x,y):
    t = Tile()
    t.x = int(math.floor(x / 256))
    t.y = int(math.floor(y / 256))
    #print"\nThe tile coordinates are x = {} and y = {}".format(t.x, t.y)
    return t

def geometry_from_tile_coords(TileX, TileY, TileZ):

    # Calculate lat, lon of upper left corner of tile
    PixelX = TileX * 256
    PixelY = TileY * 256
    MapSize = 256 * math.pow(2, TileZ)
    x = (PixelX / MapSize) - 0.5
    y = 0.5 - (PixelY / MapSize)
    lon_left = 360 * x
    lat_top = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi

    # Calculate lat, lon of lower right corner of tile
    PixelX = (TileX + 1) * 256
    PixelY = (TileY + 1) * 256
    MapSize = 256 * math.pow(2, TileZ)
    x = (PixelX / MapSize) - 0.5
    y = 0.5 - (PixelY / MapSize)
    lon_right = 360 * x
    lat_bottom = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi

    # Create Geometry
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(lon_left, lat_top)
    ring.AddPoint(lon_right, lat_top)
    ring.AddPoint(lon_right, lat_bottom)
    ring.AddPoint(lon_left, lat_bottom)
    ring.AddPoint(lon_left, lat_top)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)

    wkt_geom = poly.ExportToWkt()
    return wkt_geom