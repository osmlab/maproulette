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

var MRManager = (function () {
    var map;
    var challenge;
    var task;
    var near = Q.near;
    var difficulty = Q.difficulty;
    var taskLayer;

    /*
     * CONFIGURATION PARAMETERS
     */
    var config = {
        // The UI strings FIXME languages?
        strings         : {
            msgNextChallenge: 'Faites vos jeux...',
            msgMovingOnToNextChallenge: 'OK, moving right along...',
            msgZoomInForEdit: 'Please zoom in a little so we don\'t have to load a huge area from the API.'
        },
        // the default map options
        mapOptions      : {
            center: new L.LatLng(40, -90),
            zoom: 17
        },
        // default tile URL
        tileUrl         : 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        // default tile attribution
        tileAttrib      : '&copy; <a href=\'http://openstreetmap.org\'> OpenStreetMap</a> contributors'
    };

    /*
     * This function initializes the leaflet map.
     * identifier is the div id on the page
     */
    var createMap = function (identifier) {

        // map GeoJSON layer
        taskLayer = new L.geoJson(null, {
            onEachFeature   : function (feature, layer) {
                if(feature.properties && feature.properties.text) {
                    layer.bindPopup(feature.properties.text);
                    return layer.openPopup();
                }
            }
        });

        map = new L.Map(identifier, config.mapOptions);
        var tileLayer = new L.TileLayer(config.tileUrl, { attribution: config.tileAttrib });

        // Locate the user and define the event triggers
        map.locate({ setView: true, timeout: 1000, maximumAge: 0 });
        map.on('locationfound', function (e) {
            console.log('location found: ' + e);
        });
        map.on('locationerror', function (e) {
            console.log('location not found: ' + e.message);
        });

        map.addLayer(tileLayer);
        map.addLayer(taskLayer);
    };

    /*
     * get a random challenge with optional near and difficulty paramters
     */
    var selectChallenge = function () {

        var url = '/api/challenges/';

        if (near && difficulty) {
            console.log('we got near and difficulty');
            url += '?difficulty=' + difficulty + '&contains=' + near;
        } else if (near) {
            console.log('we got near');
            url += '?contains=' + near;
        } else if (difficulty) {
            console.log('we got difficulty');
            url += '?difficulty=' + difficulty;
        } else {
            console.log('we got neither near or difficulty');
        };

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
            url     : '/api/challenge/' + challenge.slug + '/task',
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
        humane.log(task.text);
        // let the user know where we are
        displayAdminArea();
    };

    var mqResultToString = function (addr)
    {
        var out, county, town;
        if(!addr || !(addr.town || addr.county || addr.hamlet || addr.state || addr.country)) { return 'We are somewhere on earth..' };
        out = 'We are ';
        if(addr.city != null) { out += addr.city }
        else {
            if(addr.town != null) { town = 'in ' + addr.town }
            else if(addr.hamlet != null) { town = 'in ' + addr.hamlet }
            else { town = 'somewhere in ' };
            out += town;
            if(addr.county) {
                if(addr.county.toLowerCase().indexOf('county') > -1) { county = ', ' + addr.county + ', ' }
                else { county = ', ' + addr.county + ' County, ' };
            } else { county = '' };
            out += county;
        }
        if(addr.state) { out += addr.state + ', ' };
        if(addr.country) {
            if(addr.country.indexOf('United States') > -1) { out += 'the ' };
            out += addr.country;
        };
        out += '.';
        return out;
    };

    var displayAdminArea = function() {
        var mqurl = 'http://open.mapquestapi.com/nominatim/v1/reverse?format=json&lat=' + map.getCenter().lat + ' &lon=' + map.getCenter().lng;
        $.ajax({
            url     : mqurl,
            success : function (data) { humane.log(mqResultToString(data.address)); },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
    }

    var initialize = function (identifier) {
        // create the map
        createMap(identifier);
        // and display the next task
        next();
        // get the challenge details
        getChallengeDetails();
    }

    var next = function () {
        getTask();
        drawTask();
    }

    var openIn = function (editor) {
        if (map.getZoom() < 14){
            humane.log(config.strings.msgZoomInForEdit, 3);
            return false;
        };
        var bounds = map.getBounds();
        var sw = bounds.getSouthWest();
        var ne = bounds.getNorthEast();
        if (editor == 'j') { // JOSM
            var JOSMurl = 'http://127.0.0.1:8111/load_and_zoom?left=' + sw.lng + '&right=' + ne.lng + '&top=' + ne.lat + '&bottom=' + sw.lat + '&new_layer=0&select=node' + currentWayId + ',way' + currentWayId;
            // Use the .ajax JQ method to load the JOSM link unobtrusively and alert when the JOSM plugin is not running.
            $.ajax({
                url     : JOSMurl,
                success : function (t) {
                    if (t.status!=200) {
                        humane.log('JOSM remote control did not respond. Do you have JOSM running with Remote Control enabled?');
                    } else { setTimeout('confirmRemap(\'j\')', 4000); }
                }
            });
        } else if (editor == 'o') { // OSM default
            var editURL = 'http://www.openstreetmap.org/edit?bbox=' + map.getBounds().toBBoxString();
            window.open(editURL);
            setTimeout('confirmRemap(\'p\')', 4000)
        }
    }

    return {
        init            : initialize,
        nextTask        : next
    };
}());

// initialization
function init() {
    MRManager.init('map');
};
