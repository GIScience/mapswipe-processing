# !UPDATE two new scripts: improved algorithm and faster processing

# Get your MapSwipe Data

Since, at least three different people work on every MapSwipe tile (that are the little squares) further aggregation of the answers of one tile is needed. But also adjacent tiles marked with the same answer need to be put together. We need to filter out unreliable answers and finally derive geometries that are ready to use in the HOT Tasking Manager.
The scripts in this repository can help you to download and process data that is produced by volunteers using the MapSwipe App. Nevertheless, you can also use the data we already processed for you. You can download the following datasets directly from our website:

[Overview of all projects](http://mapswipe.geog.uni-heidelberg.de/)
 [Get the data here](http://mapswipe.geog.uni-heidelberg.de/download/)

#### How can I use the processed data in Hot Tasking Manager?
We've got a **tutorial** for you, [right here](http://k1z.blog.uni-heidelberg.de/2016/11/16/integrating-mapswipe-and-hot-tasking-manager/)

#### What do I need to start?
If you want to download and process the data on your own you need python including GDAL library.
We recommend to download the **latest version of QGIS** ([download](http://www.qgis.org/en/site/forusers/download.html])) and use the OSGEO shell for executing the scripts.

# How to download and process data on your own
Let's have a general view at the functionality of the scripts before going into detail.

- Download data:
	- single project
	- specific projects
	- all projects


- Process data
	- aggregate 'yes' and 'maybe' answers --> e.g. get 'settlement' layer
	- aggregate 'bad imagery' answers --> e.g. get 'cloud' layer
	- create polygons ready to use in the HOT Tasking Manager

## ms_get script:
Your choice of projects will be downloaded and processed. All data is stored in directories named after the project id e.g.: ``output_directory/5291``
- example run:
    - ``python ms_get.py output_directory`` 
      - relative path for output directory: ``python ms_get.py output``
      - absolute path for output direcotry: ``python ms_get.py D\msf\mapswipe\output``
- First your terminal window will print you all available projects, their ID, progress, state and contributions so far.
- Then you will be prompted which project you want to get.
    - If you just want a single project, search for the id and type it in.
    - If you want several specific projects, type them in seperated by comma.
    - If you want all tasks just type in "all" (quotationmarks are obligatory).


## ms_getall script:

- The script is intened to download and process all data available by mapswipe
- Furthermore it will synchronize your local data copy with the current state of mapswipe api everytime you run it
- example run:
    - ``python ms_getall.py output_directory``
- Everytime you run it, the very first step is to create a local copy of the projects api [have a look here](api.mapswipe.org/projects.json), it'll be saved in here ``output_directory``
- IMPORTANT: If you change the output directory and theres no "projects.json" available, all projects will be downloaded. 
- Also if you face an error during download and processing, have a look into your local "projects.json" file and be sure that the specific projects you want to download are not included! 

# Detailed Information on the datasets

## raw data for each project:
- file formats: .csv .json .shp files
- information: id, user_id, project, timestamp, task_x, task_y, task_z, decision, yes_count, maybe_count, bad_imagery_count
- polygon geometry: stored in .shp files

## processed data for each project:
  1. yes_maybe_answers:
    - filtered raw data --> majority of answers is 'yes' or 'maybe'
    - file format: .geojson files
    - information: id, user_id, project, timestamp, task_x, task_y, task_z, decision, yes_count, maybe_count, bad_imagery_count
  2. bad_image:
    - filtered raw data --> majority of answers is 'bad imagery'
    - file format: .geojson files
    - information: id, user_id, project, timestamp, task_x, task_y, task_z, decision, yes_count, maybe_count, bad_imagery_count
  3. aggregation:
      - spatial aggregation / generalization of "yes_maybe_answers" geometries
      - processing is based on triangulation and geometric selection
      - file format: .geojson files
  4. final (HOT Tasking Manager input):
    - shapes for to use in HOT Tasking Manager
    - spatial aggregated layer intersected with a 500x500m grid
    - file format: .geojson files

