function get_data() {
    project_id = document.getElementById('project_id').value.toString()
    dataset = document.getElementById('dataset').value
    url = 'http://mapswipe.heigit.org/processing/data/' + project_id + '/' + dataset + '_' + project_id + '.geojson'
    var win = window.open(url);
    win.focus();
}


function show_maps(){
    var maps = ['hot_tm_geometries_map', 'yes_maybe_results_map', 'bad_imagery_results_map', 'raw_results_map']
    for (var i = 0; i < maps.length; i++) {
        show_map(maps[i])
}
};


function add_example_layer(map, div_id_name) {
    if (div_id_name == 'hot_tm_geometries_map') {
        url = 'examples/hot_tm_tasks_examples.geojson'
    } else if (div_id_name == 'yes_maybe_results_map') {
       url = 'examples/yes_maybe_examples.geojson'
    } else if (div_id_name == 'bad_imagery_results_map') {
       url = 'examples/bad_image_examples.geojson'
    } else {
        url = 'examples/results_examples.geojson'
    }
    div_id_name = new L.GeoJSON.AJAX(url);
    div_id_name.on("data:loaded", function() {
        map.fitBounds(div_id_name.getBounds());}
        )
    map.addLayer(div_id_name);

}

function show_map(div_id){
    // Create the map
    div_id_name = div_id
    var div_id = L.map(div_id_name, {
      center: [0, 0],
      zoom: 3,
      maxZoom: 18,
    });

    div_id.scrollWheelZoom.disable()
    createBaseLayers(div_id);
    add_example_layer(div_id, div_id_name);
}


//Loads baselayers (Korona OSM, Korona OSM Greyscale, Bin Imagery), adds them to map and mapControl
function createBaseLayers(map) {
      //var osmUrl='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
      var osmUrl='http://korona.geog.uni-heidelberg.de/tiles/roads/x={x}&y={y}&z={z}';
      var osmAttrib='Map data © <a target="_blank" href="http://openstreetmap.org">OpenStreetMap</a> contributors, tiles <a target="_blank" href="http://www.geog.uni-heidelberg.de/gis/index_en.html">GIScience Research Group @ Heidelberg University</a>';
      osm = new L.TileLayer(osmUrl, {attribution: osmAttrib});

      var osmGreyUrl = 'https://korona.geog.uni-heidelberg.de/tiles/roadsg/x={x}&y={y}&z={z}';
      osmGrey = new L.TileLayer(osmGreyUrl, {attribution: osmAttrib});
      map.addLayer(osm);

      // Bing Layer
      var bing_key = 'AopsdXjtTu-IwNoCTiZBtgRJ1g7yPkzAi65nXplc-eLJwZHYlAIf2yuSY_Kjg3Wn'
      bing = L.tileLayer.bing(bing_key)


      var baseLayers = {
      "Microsoft Bing": bing,
      "OpenStreetMap": osm,
      "OpenStreetMap Greyscale": osmGrey
      };

      var overlays = {
      }
      mapControl = new L.control.layers(baseLayers,overlays, {collapsed: false});

      map.addControl(mapControl);

      mapControl._overlaysList.onchange = function() { //adjusts the legend to the change in layers

        for (i = 3; i < mapControl._layers.length; i++) { // the 3 stands for the 3 baseLayers. This should be solved dynamicly
            if (mapControl._layers[i].layer._container == undefined || typeof mapControl._layers[i].layer._container == null){
                document.getElementById(mapControl._layers[i].name).style.display = 'none';

            }
            else {
              document.getElementById(mapControl._layers[i].name).style.display = 'block';
            }
        }
      }
    }

