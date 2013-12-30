// get URL parameters
// http://stackoverflow.com/a/979995
var Q = (function () {
    // This function is anonymous, is executed immediately and
    // the return value is assigned to Q!
    var i = 0;
    var query_string = {};
    var query = window.location.search.substring(1);
    var vars = query.split('&');
    while (i < vars.length) {
        var pair = vars[i].split('=');
        // If first entry with this name
        if (typeof query_string[pair[0]] === 'undefined') {
            query_string[pair[0]] = pair[1];
            // If second entry with this name
        } else if (typeof query_string[pair[0]] === 'string') {
            var arr = [ query_string[pair[0]], pair[1] ];
            query_string[pair[0]] = arr;
            // If third or later entry with this name
        } else {
            query_string[pair[0]].push(pair[1]);
        }
        i++;
    }
    return query_string;
}());

var MRHelpers = (function () {
    var constructJosmUri = function (bounds, features) {
        var nodes = [];
        var ways = [];
        var sw = bounds.getSouthWest();
        var ne = bounds.getNorthEast();
        var uri = 'http://127.0.0.1:8111/load_and_zoom?left=' + sw.lng + '&right=' + ne.lng + '&top=' + ne.lat + '&bottom=' + sw.lat + '&new_layer=0&select=';

        for (f in features) {
            var feature = features[f];
            switch (feature.geometry.type) {
                case 'Point':
                    url += 'node' + feature.properties.osmid;
                    break;
                case 'LineString':
                    url += 'way' + feature.properties.osmid;
                    break;
            }
        }
        return uri;
    };

    var addComma = function(str) {
        return (str.match(/\,\s+$/) || str.match(/in\s+$/))?'':', ';
    }

    var mqResultToString = function (addr) {
        var out, county, town;
        if(!addr || !(addr.town || addr.county || addr.hamlet || addr.state || addr.country)) { return 'We are somewhere on earth..' };
        out = 'We are ';
        if(addr.city != null) { out += 'in ' + addr.city }
        else if (addr.town != null) { out += 'in ' + addr.town }
        else if (addr.hamlet != null) { out + 'in ' + addr.hamlet  }
        else { out += 'somewhere in ' };
        out += addComma(out); 
        if(addr.county) {
            if(addr.county.toLowerCase().indexOf('county') > -1) { out += addr.county }
            else { out += addr.county + ' County' };
        };
        out += addComma(out); 
        if(addr.state) { out += addr.state };
        out += addComma(out); 
        if(addr.country) {
            if(addr.country.indexOf('United States') > -1) { out += 'the ' };
            out += addr.country;
        };
        out += '.';
        return out;
    };

    var openInJOSM = function (bounds, features) {
        var josmUri = constructJosmUri(bounds, features);
        console.log('opening in JOSM');
        // Use the .ajax JQ method to load the JOSM link unobtrusively and alert when the JOSM plugin is not running.
        $.ajax({
            url     : josmUri,
            success : function (t) {
                if (t.status!=200) {
                    notify.log('JOSM remote control did not respond. Do you have JOSM running with Remote Control enabled?');
                } else { setTimeout('confirmRemap(\'j\')', 4000); }
            }
        });
    };

    return {
        mqResultToString    : mqResultToString,
        openInJOSM          : openInJOSM
    }
}());

var MRConfig = (function () {
    // the UI strings
    return {
        strings:  {
            msgNextChallenge: 'Faites vos jeux...',
            msgMovingOnToNextChallenge: 'OK, moving right along...',
            msgZoomInForEdit: 'Please zoom in a little so we don\'t have to load a huge area from the API.'
        },

        // the default map options
        mapOptions: {
            center: new L.LatLng(40, -90),
            zoom: 17
        },

        // default tile URL
        tileUrl: 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',

        // default tile attribution
        tileAttrib: '&copy; <a href=\'http://openstreetmap.org\'> OpenStreetMap</a> contributors',

        // minimum zoom level for enabling edit buttons
        minZoomLevelForEditing: 14
    };
}());

var MRManager = (function () {
    var map;
    var challenge;
    var task;
    var near = (Q.lon && Q.lat) ? { 'lon': parseFloat(Q.lon), 'lat': parseFloat(Q.lat) } : {};
    var difficulty = parseInt(Q.difficulty);
    var taskLayer;

    // define humane notification instance
    var notify = humane.create({ timeout: 1500 });

    /* 
     * A helper function to construct the URL parameters for location and difficulty
     * if it is for a challenge, we need the difficulty as well as the location.
     */
    var constructUrlParameters = function (isChallenge) {
        var urlParams = '?';
        if (typeof near.lat === 'number' && typeof near.lon === 'number') { // this is not quite accurate but good enough for a casual check.
            urlParams += 'lon=' + near.lon + '&lat=' + near.lat + '&';
        };
        if ([1,2,3].indexOf(difficulty) > -1 && isChallenge) { // difficulty must be 1,2,3
            urlParams += 'difficulty=' + difficulty };
        return urlParams;
    }

    /*
     * This function initializes the leaflet map, gets the user location, and loads the first task.
     * A challenge is selected based on the user location, the URL parameter, or on the server side using the stored OSM home location.
     * identifier is the div id on the page
     */
    var init = function (identifier) {

        // a friendly welcome
        notify.log(['Welcome to MapRoulette!']);
 
        // map GeoJSON layer
        taskLayer = new L.geoJson(null, {
            onEachFeature   : function (feature, layer) {
                if(feature.properties && feature.properties.text) {
                    layer.bindPopup(feature.properties.text);
                    return layer.openPopup();
                }
            }
        });

        // initialize the map
        map = new L.Map(identifier, MRConfig.mapOptions);

        // and the tile layer
        var tileLayer = new L.TileLayer(MRConfig.tileUrl, { attribution: MRConfig.tileAttrib });

        // Locate the user and define the event triggers
        map.locate({ setView: false, timeout: 10000, maximumAge: 0 });
        // If the location is found, let the user know, and store.
        map.on('locationfound', function (e) {
            console.log('location found: ' + e.latlng);
            near.lat = parseFloat(e.latlng.lat);
            near.lon = parseFloat(e.latlng.lng);
            notify.log('We found your location. You next task will be closer to home!');
        });
        // If the location is not found, meh.
        map.on('locationerror', function (e) {
            console.log('location not found or not permitted: ' + e.message);
        });

        // Add both the tile layer and the task layer to the map
        map.addLayer(tileLayer);
        map.addLayer(taskLayer);

        // now load a task (this will select a challenge first)
        nextTask();

        // and request the challenge details and stats (slow)
        getChallengeDetails();
    };

    /*
     * get a random challenge with optional near and difficulty paramters
     */
    var selectChallenge = function () {

        var url = '/api/challenges/' + constructUrlParameters();

        // fire the request for a new challenge with the contructed URL
        $.ajax(
        {
            url     : url,
            async   : false,
            success : function (data) { challenge = data[0]; },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
    };

    /*
     * get the selected challenge
     */
     var getChallengeDetails = function () {
        // check if we have a challenge, if not get one.
        if (typeof challenge === 'undefined') {
            selectChallenge();
        };

        // request the challenge details
        console.log('getting challenge details');
        url = '/api/challenge/' + challenge.slug;
        $.ajax({
            url     : url,
            success : function (data) {
                $.each(data, function(key, value) {
                    challenge[key] = value;
                });
                // update the challenge detail UI elements
                $('#challenge_title').text(challenge.title);
                $('#challenge_description').text(challenge.description);
                // and move on to get the stats
                getChallengeStats()
            },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
    }

    var getChallengeStats = function () {
        // now get the challenge stats
        console.log('getting challenge stats');
        url = '/api/challenge/' + challenge.slug + '/stats';
        challenge.stats = {};
        $.ajax({
            url     : url,
            success : function (data) {
                $.each(data, function(key, value) {
                    challenge.stats[key] = value;
                });
                // update the stats UI elements
                $('#stats #total').text(challenge.stats.total);
                $('#stats #available').text(challenge.stats.available);
            },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
    };

    /*
     * get a task for the current challenge
     */
    var getTask = function () {

        // check if we have a challenge, if not get one.
        if (typeof challenge === 'undefined') {
            selectChallenge();
        };

        // get a task
        $.ajax({
            url     : '/api/challenge/' + challenge.slug + '/task' + constructUrlParameters(),
            async   : false,
            success: function (data) { task = data },
            error: function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });

        //...and its geometries
        $.ajax({
            url     : '/api/challenge/' + challenge.slug + '/task/' + task.id + '/geometries',
            async   : false,
            success : function (data) { task.features = data.features; },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
    };

    /*
     * draw the task features onto the map canvas
     */
    var drawTask = function () {
        // clear the previous task from the layer
        taskLayer.clearLayers();

        // if we don't have a task, get one
        if (typeof task === 'undefined') {
            console.log('we don\'t have a task');
            return false;
        };

        // draw all features of this task on the task layer
        for(var i = 0; i < task.features.length; i++) {
            feature = task.features[i];
            taskLayer.addData(feature);
            console.log('geojson layer now has ' + taskLayer.getLayers().length + ' things.');
        }
        // fit the map snugly to the task features
        map.fitBounds(taskLayer.getBounds().pad(0.2));
        // show the task text as a notification
        notify.log(task.text, { timeout: 3000 });
        // let the user know where we are
        displayAdminArea();
    };

    var displayAdminArea = function() {
        var mqurl = 'http://open.mapquestapi.com/nominatim/v1/reverse?format=json&lat=' + map.getCenter().lat + ' &lon=' + map.getCenter().lng;
        $.ajax({
            url     : mqurl,
            success : function (data) { notify.log(MRHelpers.mqResultToString(data.address)); },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
    }

    var nextTask = function () {
        getTask();
        drawTask();
    }

    var openTaskInEditor = function (editor) {
        if (map.getZoom() < MRConfig.minZoomLevelForEditing){
            notify.log(MRConfig.strings.msgZoomInForEdit, 3);
            return false;
        };
        console.log('opening in ' + editor);
        if (editor === 'j') { MRHelpers.openInJOSM(map.getBounds(), task.features) }
        else { // OSM default
            var editURL = 'http://www.openstreetmap.org/edit?bbox=' + map.getBounds().toBBoxString();
            window.open(editURL);
            setTimeout('confirmRemap(\'p\')', 4000)
        }
    }

    return {
        init            : init,
        nextTask        : nextTask,
        openTaskInEditor: openTaskInEditor
    };
}());

// initialization
function init() {
    MRManager.init('map');
};
