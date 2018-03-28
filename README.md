# MapSwipe Processing Documentation

This project can help you to download processed data that is produced by volunteers using the MapSwipe App. We filter out unreliable answers and derive geometries that are ready to use in the HOT Tasking Manager.

Since, at least three different people work on every MapSwipe tile (that are the little squares) further aggregation of the answers of one tile is needed. But also adjacent tiles marked with the same answer need to be put together. We need to filter out unreliable answers and finally derive geometries that are ready to use in the HOT Tasking Manager.
The scripts in this repository can help you to download and process data that is produced by volunteers using the MapSwipe App. Nevertheless, you can also use the data we already processed for you. You can download the following datasets directly from our website:


## How to download and process data on your own
You can run the complete import script like this:
* `python run_mapswipe_processing.py -p 13508 -mo all -t geojson -o data/`
* `python run_mapswipe_processing.py -a -mo all -t geojson -o data/`

Parameters:
* `-p` or `--projects`: project id(s) as integer. Only projects corresponding to the provided ids will be downloaded and/or updated.
* `-a` or `--all_projects`: flag to download all projects which changed since last download.
* `-mo` or `--modus`: chose which dataset to download. Options: `'hot_tm', 'download', 'dissolve', 'all'`
* `-t` or `--output_type`: chose the data format for the output. Options: `'hot_tm', 'download', 'dissolve', 'all'`
* `-o` or `--output_path`: chose the location/path for the output.

## Output Data Description and Examples
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

