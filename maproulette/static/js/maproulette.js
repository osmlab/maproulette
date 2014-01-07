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

var MRNotifier = function () {

    // defaults for noty engine
    $.noty.defaults = {
        layout: 'top',
        theme: 'mapRouletteTheme',
        type: 'alert',
        text: '', 
        dismissQueue: true,
        template: '<div class="noty_message"><span class="noty_text"></span><div class="noty_close"></div></div>',
        animation: {
            open: {height: 'toggle'},
            close: {height: 'toggle'},
            easing: 'swing',
            speed: 500 
        },
        timeout: 5000, 
        force: false,
        modal: false,
        maxVisible: 5, 
        killer: false, 
        closeWith: ['click'],
        callback: {
            onShow: function() {},
            afterShow: function() {},
            onClose: function() {},
            afterClose: function() {}
        },
        buttons: false // an array of buttons
    };
    // play a notification using options
    // the options are specific to the notification framework used.
    // currently we use noty, see http://ned.im/noty/#options
    var play = function (text, options) {
        // if an array (of lines) was passed in, join them
        if( Object.prototype.toString.call( text ) === '[object Array]' ) {
            text = text.join('<br />');
        }
        // if no options were passed in, initialize options object
        if (!options) var options = {};
        options.text = text;
        var n = $('.notifications').noty(options);
        return n;
    }

    // clear the notification queue
    var clear = function () {
        $.noty.clearQueue();
    }

    // cancel a notification by id
    var close = function(n) {
        if (typeof n === 'noty') n.close();
    }

    return {
        play            : play,
        clear           : clear,
        close           : close,
    }
}();

var MRButtons = function () {

    var buttonTypes = {
        'fixed'         : 'I fixed it!',
        'skipped'       : 'Too difficult / Couldn\'t see',
        'falsepositive' : 'It was not an error',
        'alreadyfixed'  : 'Someone beat me to it'  
    };

    var makeButton = function (buttonType) {
        if (!(buttonType in buttonTypes)) { return false };
        return '<div class=\'button\' onClick=MRManager.nextTask(\'' + buttontype + '\') id=\'' + buttonType + '\'>' + buttonTypes[buttonType] + '</div>';
    };

    var makeButtons = function () {
        var buttonHTML = '';
        for (key in buttonTypes) { 
            buttonHTML += '<div class=\'button\' onClick=MRManager.nextTask(\'' + key + '\') id=\'' + key + '\'>' + buttonTypes[key] + '</div>\n';
        };
        return buttonHTML;
    };

    return {
        makeButton  : makeButton,
        makeButtons : makeButtons
    };

}();

var MRHelpers = (function () {

    var addComma = function(str) {
        return (str.match(/\,\s+$/) || str.match(/in\s+$/))?'':', ';
    }

    var mqResultToString = function (addr) {
        var out, county, town;
        if(!addr || !(addr.town || addr.county || addr.hamlet || addr.state || addr.country)) { return 'We are somewhere on earth..' };
        out = 'We are ';
        if(addr.city != null) { out += 'in ' + addr.city }
        else if (addr.town != null) { out += 'in ' + addr.town }
        else if (addr.hamlet != null) { out += 'in ' + addr.hamlet }
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

    return {
        mqResultToString    : mqResultToString,
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
            zoom: 4
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
    var editor;
    var near = (Q.lon && Q.lat) ? { 'lon': parseFloat(Q.lon), 'lat': parseFloat(Q.lat) } : {};
    var difficulty = parseInt(Q.difficulty);
    var taskLayer;

    // create a notifier
    notify = MRNotifier

    // are we logged in?
    this.loggedIn = false;

    var constructJosmUri = function () {
        var bounds = map.getBounds();
        var nodes = [];
        var ways = [];
        var sw = bounds.getSouthWest();
        var ne = bounds.getNorthEast();
        var uri = 'http://127.0.0.1:8111/load_and_zoom?left=' + sw.lng + '&right=' + ne.lng + '&top=' + ne.lat + '&bottom=' + sw.lat + '&new_layer=0&select=';

        for (f in task.features) {
            var feature = task.features[f];
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

    var openInJOSM = function () {
        var josmUri = constructJosmUri();
        // Use the .ajax JQ method to load the JOSM link unobtrusively and alert when the JOSM plugin is not running.
        $.ajax({
            url     : josmUri,
            success : function (t) {
                if (t.indexOf('OK') === -1) {
                    notify.play('JOSM remote control did not respond. Do you have JOSM running with Remote Control enabled?');
                } else { 
                    console.log('the data was loaded in JOSM, now waiting for callback');
                    updateTask('editing');
                    setTimeout(confirmRemap, 4000); 
                }
            }
        });
    };

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
        var opts = {timeout: false};
        if (!this.loggedIn) opts.callback = {afterClose: function(){location.href=$('#loginlink').attr('href')}};
        var lines = ['Welcome to MapRoulette!'];
        if (typeof this.loggedIn === 'undefined' || this.loggedIn === false) lines.push('<em>Please log in to get started.</em>','(You will be logging in via OpenStreetMap.)');
        else lines.push('You are logged in as ' + this.loggedIn);
        
        notify.play(lines, opts);
 
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

        // Add both the tile layer and the task layer to the map
        map.addLayer(tileLayer);
        map.addLayer(taskLayer);

        if (this.loggedIn) {
            // now load a task (this will select a challenge first)
            nextTask();

            // and request the challenge details and stats (slow)
            getChallengeDetails();
        };
    };

    /*
     * get a random challenge with optional near and difficulty paramters
     */
    var selectChallenge = function (all) {

        console.log('selecting a challenge');
        var url = '/api/challenges/' + constructUrlParameters();

        if (all) url += 'all=true';

        console.log(url);

        // fire the request for a new challenge with the contructed URL
        $.ajax(
        {
            url     : url,
            async   : false,
            success : function (data) { 
                console.log(data.length + ' challenges returned');
                // select a random challenge
                challenge = data[Math.floor(Math.random() * data.length)]; 
                console.log(challenge);
            },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
        if (!challenge) {
            // if we got no challenges, there is something wrong.
            console.log('no challenges returned');
            notify.play('There are no local challenges available. MapRoulette will find you a random challenge to start you off with.', {addnCls: 'humane-maproulette-info'})
            selectChallenge(true);
        };
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

    var updateTask = function (action) {
        // if we don't have a task yet, return immediately
        if (!task) { return false };

        var payload = {
            "action": action,
            "editor": editor
        };
        $.ajax({
            url     : "/api/challenge/" + challenge.slug + "/task/" + task.id,
            type    : "POST",
            data    : payload,
            success : function (data) {
                console.log('task ' + task.id + ' updated')
            },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
        

    }

    /*
     * get a task for the current challenge
     */
    var getTask = function () {

        // check if we have a challenge, if not get one.
        if (typeof challenge === 'undefined') {
            selectChallenge();
        };
        console.log('challenge got: ' + challenge);
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
        notify.play(task.text);
        // let the user know where we are
        displayAdminArea();
    };

    var displayAdminArea = function() {
        var mqurl = 'http://open.mapquestapi.com/nominatim/v1/reverse?format=json&lat=' + map.getCenter().lat + ' &lon=' + map.getCenter().lng;
        $.ajax({
            url     : mqurl,
            success : function (data) { notify.play(MRHelpers.mqResultToString(data.address)); },
            error   : function (jqXHR, textStatus, errorThrown) { console.log('ajax error'); }
        });
    }

    var nextTask = function (action) {
        // make the done dialog disappear if it is there
        $('.donedialog').delay(1000).fadeOut();
        // update the outgoing task
        updateTask(action);
        // get the next task
        getTask();
        // and draw it
        drawTask();
        // update challenge stats
        getChallengeStats()
    };

    var openTaskInEditor = function (editor) {
        editor = editor;
        if (map.getZoom() < MRConfig.minZoomLevelForEditing){
            notify.play(MRConfig.strings.msgZoomInForEdit);
            return false;
        };
        console.log('opening in ' + editor);
        if (editor === 'j') { openInJOSM() }
        else { // OSM default
            //edit#map=16/31.8289/-112.5948
            var editURL = 'http://osm.org/edit#map=' + map.getZoom() + '/' + map.getCenter().lat + '/' + map.getCenter().lng;
            // open a new window with the edit URL
            window.open(editURL);
            // update the task
            updateTask('editing');
            // display the confirmation dialog
            setTimeout(confirmRemap, 4000);
        }
    };

    var presentDoneDialog = function() {
        var d = challenge.done_dlg;
        
        // if there is no done dialog info, bail
        // FIXME we should be reverting to a default
        if (typeof d === 'undefined') { return false };
        
        var dialogHTML = '<div class=\'text\'>' + d.text + '</div>';

        if (typeof d.buttons === 'string' && d.buttons.length > 0) {
            var buttons = d.buttons.split('|');
            for (var i = 0; i < buttons.length; i++) {
                dialogHTML += MRButtons.makeButton(buttons[i]);
            };
        } else {
            dialogHTML += MRButtons.makeButtons();
        }
        $('.donedialog').html(dialogHTML).fadeIn();
    }

    var geolocateUser = function () {
        // Locate the user and define the event triggers
        map.locate({ setView: false, timeout: 10000, maximumAge: 0 });
        // If the location is found, let the user know, and store.
        map.on('locationfound', function (e) {
            console.log('location found: ' + e.latlng);
            near.lat = parseFloat(e.latlng.lat);
            near.lon = parseFloat(e.latlng.lng);
            notify.play('We found your location. MapRoulette will try and give you tasks closer to home if they are available.');
        });
        // If the location is not found, meh.
        map.on('locationerror', function (e) {
            console.log('location not found or not permitted: ' + e.message);
        });
    };

    var confirmRemap = function () {
        console.log('confirming remap');
        presentDoneDialog();
    };

    return {
        init            : init,
        nextTask        : nextTask,
        openTaskInEditor: openTaskInEditor,
        geolocateUser   : geolocateUser, 
    };
}());

// initialization
function init(elemName) {
    MRManager.init(elemName);
};
