

#get area of ms tiles. Area depends on the geog. alt / y
#task_y refers to the upper left point
#see https://msdn.microsoft.com/en-us/library/bb259689.aspx

# task_y ranges from 0 to 2^level-1
#for level = 18 we have task_y = 0 at the north pole and task_z = 262143

#get libs
from osgeo import ogr, osr
import numpy as np
import math
import json
import matplotlib.pyplot as plt
#import tile_functions
#pixels to meter, length of a tile on a lat and lvl
def toMeter(lat, lvl):
    return (np.cos(lat * np.pi/180) * 2 * np.pi * 6378137) / (256 * 2**lvl) * 256

# get geom in webm
# lvl: task_z, elvel of detail/zoom
# x: task_x
# y: task_y
def square(x, y, lvl):
    ring = ogr.Geometry(ogr.wkbLinearRing)
    sidelength = toMeter(0, 18)
    x0 = x *sidelength
    y0 = y * sidelength
    ring.AddPoint(x0, y0)
    ring.AddPoint(x0 + sidelength, y0)
    ring.AddPoint(x0 - sidelength, y0)
    ring.AddPoint(x0 - sidelength, y0 - sidelength)
    ring.AddPoint(x0, y0)
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    return poly

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
    return poly


    def writeTiles():
        x = 131070
        lvl = 18
        multipolygon = ogr.Geometry(ogr.wkbGeometryCollection)

        outDriver = ogr.GetDriverByName('GeoJSON')
        outDataSource = outDriver.CreateDataSource('tiles.geojson')
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(3857)
        outLayer = outDataSource.CreateLayer('tiles.geojson', srs, geom_type=ogr.wkbPolygon)
        featureDefn = outLayer.GetLayerDefn()
        field_project = ogr.FieldDefn('task_y', ogr.OFTInteger)
        outLayer.CreateField(field_project)
        field_project = ogr.FieldDefn('task_x', ogr.OFTInteger)
        outLayer.CreateField(field_project)
        field_project = ogr.FieldDefn('task_z', ogr.OFTInteger)
        outLayer.CreateField(field_project)
        field_project = ogr.FieldDefn('area', ogr.OFTReal)
        outLayer.CreateField(field_project)
        field_project = ogr.FieldDefn('perimeter', ogr.OFTReal)
        outLayer.CreateField(field_project)
        field_project = ogr.FieldDefn('lat_x', ogr.OFTReal)
        outLayer.CreateField(field_project)
        field_project = ogr.FieldDefn('lat_y', ogr.OFTReal)
        outLayer.CreateField(field_project)

        for y in range(0, 2 ** (lvl - 1) - 1, 32):  # 0, 2**lvl-1 for complete stripe
            # Create ring #1
            poly = (geometry_from_tile_coords(x, y, lvl))
            outFeature = ogr.Feature(featureDefn)
            outFeature.SetGeometry(poly)

            outFeature.SetField('task_z', lvl)
            outFeature.SetField('task_y', y)
            outFeature.SetField('task_x', x)

            outLayer.CreateFeature(outFeature)
            print(y)

        # Create polygon #1

        outFeature = None
        outDataSource = None
##the functions above can be found in tile_functions


def plot(path):
    #read json
    json_data = open(path).read()
    data = json.loads(json_data)

    features = data['features']
    center_y = []
    task_y = []
    area = []
    perimeter = []
    length_x = []
    length_y = []
    for f in features:
        #y values: task and geogaphical
        task_y.append(f['properties']['task_y'])
        center_y.append(f['properties']['center_y'])

        # measurements
        area.append(f['properties']['area_in_sqm'])
        perimeter.append(f['properties']['perimeter_in_m'])
        length_x.append(f['properties']['length_x'])
        length_y.append(f['properties']['length_y'])

    plt.plot(area, center_y,)
    plt.ylabel('Geographical Latitude [°]')
    plt.xlabel(('Area [m²]'))
    #plt.axis([0, 6, 0, 20])
    plt.show()
    #for f in data['features']:
        #print(f['properties'])
     #   for d in f['properties']:
      #      print(d)
    print('End')

def main():
    plot("examples\\tiles.geojson")



main()

