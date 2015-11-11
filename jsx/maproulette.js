/** @jsx React.DOM */

var ReactCSSTransitionGroup = React.addons.CSSTransitionGroup;
var USE_SKOBBLER = false;

marked.setOptions({
  gfm: true,
  tables: true,
  breaks: false,
  pedantic: false,
  sanitize: true,
  smartLists: true,
  smartypants: true
});

toastr.options = {
  "closeButton": false,
  "debug": false,
  "newestOnTop": false,
  "progressBar": false,
  "toastClass": "notification",
  "positionClass": "toast-top-left",
  "preventDuplicates": false,
  "onclick": null,
  "showDuration": "300",
  "hideDuration": "1000",
  "timeOut": "3000",
  "extendedTimeOut": "0",
  "showEasing": "swing",
  "hideEasing": "linear",
  "showMethod": "fadeIn",
  "hideMethod": "fadeOut"
}

// React Components
var Button = React.createClass({
  render: function(){
    return (
      <div className="button"
           onClick={this.props.onClick}>
        {this.props.children}
      </div>
    );
  }});

var AreaSelectButton = React.createClass({
  render: function(){
    return (
      <div className="button"
           onClick={this.props.onClick}>
        {this.props.userHasArea ? 'I want to clear my editing area or select a new one' : 'I want to select an area to work in'}
      </div>
    );
  }});

var ActionButton = React.createClass({
    render: function(){
        var action = this.props.action;
        return (
            <div className="button"
            onClick={function(){MRManager.nextTask(action)}}>
            {this.props.children}
            </div>)
    }
});

var CancelButton = React.createClass({
  render: function(){
    return (
      <div className="button cancel"
           onClick={this.props.onClick}>
        {this.props.children}
      </div>
    );
  }});

var DifficultyBadge = React.createClass({
    render: function(){
        var value = parseInt(this.props.difficulty);
        switch (value) {
            case 1:
            return (
                <span className="difficultyBadge">
                <span className="d1">
                EASY</span></span>
            );
            case 2:
            return (
                <span className="difficultyBadge">
                <span className="d2">
                MODERATE</span></span>
            );
            case 3:
            return (
                <span className="difficultyBadge">
                <span className="d3">
                HARD</span></span>);
        };
    }
});

var ChallengeBox = React.createClass({

    getInitialState: function () {
        return {
            stats: {"total": 0, "unfixed": 0}
        }
    },

    componentWillMount: function () {
        $.ajax({
            url: "/api/challenge/" + this.props.challenge.slug + "/summary",
            dataType: 'json',
            success: function(data) {
                this.setState({"stats": data})
                if (this.state.stats.total == 0 || this.state.stats.unfixed == 0) {
                    this.getDOMNode().style.display = "none";
                };
            }.bind(this)
        })
    },

    render: function(){
        var slug = this.props.challenge.slug;
        var pickMe = function(){
            MRManager.userPickChallenge(slug);
        };
        return(
            <Button onClick={pickMe}>
            <div className="challengeBox">
            <span className="title">{this.props.challenge.title}</span>
            <DifficultyBadge difficulty={this.props.challenge.difficulty} />
            <p>{this.props.challenge.blurb}</p>
            <p>total tasks: {this.state.stats.total}, available: {this.state.stats.unfixed}</p>
            </div>
            </Button>
        );
    }
});

var ChallengeSelectionDialog = React.createClass({
    getInitialState: function() {
        return {
            challenges: [],
            usersettings: {}};
        },
    componentWillMount: function(){
        $.ajax({
            url: "/api/challenges",
            dataType: 'json',
            success: function(data) {
                var active_challenges = data.filter(function (elem) {
                    return elem.active;
                }).sort(function(a, b){
                    return(a.difficulty - b.difficulty)
                });
                this.setState({challenges: active_challenges});
            }.bind(this)
        })
        $.ajax({
            url: "/api/me",
            dataType: 'json',
            success: function(data) {
                this.setState({usersettings: data});
            }.bind(this)
        })
    },
    render: function(){
        var challengeBoxes = this.state.challenges.map(function(challenge){
            return <ChallengeBox challenge={challenge} />;
        });
        return (
            <ReactCSSTransitionGroup transitionName="dialog">
                <div>
                    <h2>Pick a different challenge</h2>
                        <AreaSelectButton userHasArea={this.state.usersettings['lon'] != null} onClick={closeDialog(MRManager.userPickEditLocation)}></AreaSelectButton>
                        {challengeBoxes}
                    <CancelButton onClick={MRManager.readyToEdit}>Nevermind</CancelButton>
                </div>
            </ReactCSSTransitionGroup>
        );
    }}
);

var DefaultDoneDialog = React.createClass({
  render: function(){
      return (
          <div>
          <p>The area is now loaded in your OSM editor. See if you can fix it, and then return to MapRoulette.</p>
          <p><em>Please make sure you save (iD) or upload (JOSM) your work after each fix!</em></p>
          <ActionButton action="fixed">I fixed it!</ActionButton>
          <ActionButton action="skipped">Too difficult/Couldn&#39;t see</ActionButton>
          <ActionButton action="falsepositive">It was not an error</ActionButton>
          <ActionButton action="alreadyfixed">Someone beat me to it</ActionButton>
          </div>)
  }
});

// Misc functions

var signIn = function(){
  //location.reload();
  location.href="/signin"
}

// Decorator to close the dialog box and run the specified function.
// If it's a react component, unmounts it too
var closeDialog = function(fun){
    return function(){
        $('#dialog').fadeOut({
            complete: function(){
                fun();
                // If this is a react component, we don't need it anymore
                React.unmountComponentAtNode(document.getElementById('dialog'));
            }
        });
    }
};

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
            query_string[pair[0]] = [query_string[pair[0]], pair[1]];
            // If third or later entry with this name
        } else {
            query_string[pair[0]].push(pair[1]);
        }
        i++;
    }
    return query_string;
}());

var MRHelpers = (function () {

    var addComma = function (str) {
        return (str.match(/\,\s+$/) || str.match(/in\s+$/)) ? '' : ', ';
    };

    var mqResultToString = function (addr) {
        // Convert a MapQuest reverse geocoding result to a human readable string.
        var out, county, town;
        if (!addr || !(addr.town || addr.county || addr.hamlet || addr.state || addr.country)) {
            return 'We are somewhere on earth..'
        }
        out = 'We are ';
        if (addr.city != null) {
            out += 'in ' + addr.city
        } else if (addr.town != null) {
            out += 'in ' + addr.town
        } else if (addr.hamlet != null) {
            out += 'in ' + addr.hamlet
        } else {
            out += 'somewhere in '
        }
        out += addComma(out);
        if (addr.county) {
            if (addr.county.toLowerCase().indexOf('county') > -1) {
                out += addr.county
            } else {
                out += addr.county + ' County'
            }
        }
        out += addComma(out);
        if (addr.state) {
            out += addr.state
        }
        out += addComma(out);
        if (addr.country) {
            if (addr.country.indexOf('United States') > -1) {
                out += 'the '
            }
            out += addr.country;
        }
        out += '.';
        return out;
    };

    return {
        mqResultToString: mqResultToString,
    }
}());

var MRConfig = (function () {
    return {
        // the UI strings
        strings: {
            msgNextChallenge: 'Faites vos jeux...',
            msgMovingOnToNextChallenge: 'OK, moving right along...',
            msgZoomInForEdit: 'Please zoom in a little so we don\'t have to load a huge area from the API.'
        },

        // the default map options
        mapOptions: {
            center: new L.LatLng(40, -90),
            zoom: 4,
            keyboard: false,
            // Below are Skobbler API specific options. If you don't have a Skobbler API key, set USE_SKOBBLER to false and ignore these.
            apiKey: 'CHANGE ME',
            mapStyle: 'lite'
        },

        // the collection of tile layers.
        // Each layer should have an url and attribution property.
        // the key will be the title in the layer picker control
        // where underscores in the key will be translated to spaces.
        tileLayers: {
            OpenStreetMap: {
                url: "http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                attribution: "&copy; <a href=\'http://openstreetmap.org\'> OpenStreetMap</a> contributors"},
            ESRI_Aerial: {
                url: "http://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attribution: "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"}
            },

        // minimum zoom level for enabling edit buttons
        minZoomLevelForEditing: 14
    };
}());

var MRManager = (function () {
        var map;
        var editArea;
        var MAX_EDIT_RADIUS = 512000 // 512 km
        var challenges = [];
        var challenge = {};
        var task = {};
        var editor;
        var near = (Q.lon && Q.lat) ? {
            'lon': parseFloat(Q.lon),
            'lat': parseFloat(Q.lat)
        } : {};
        var difficulty = parseInt(Q.difficulty);
        var taskLayer = new L.geoJson(null, {
            onEachFeature: function (feature, layer) {
                if (feature.properties && feature.properties.text) {
                    layer.bindPopup(feature.properties.text);
                    return layer.openPopup();
                }
            }
        });

        // are we logged in?
        this.loggedIn = false;

        var constructJosmUri = function () {
            var bounds = map.getBounds();
            var nodes = [];
            var ways = [];
            var relations = [];
            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var uri = 'http://127.0.0.1:8111/load_and_zoom?left=' + sw.lng + '&right=' + ne.lng + '&top=' + ne.lat + '&bottom=' + sw.lat + '&new_layer=0&select=';
            var selects = [];

            for (f in task.features) {
                var feature = task.features[f];
                if (!feature.properties.osmid) {
                    continue;
                }
                switch (feature.geometry.type) {
                case 'Point':
                    selects.push('node' + feature.properties.osmid);
                    break;
                case 'LineString':
                    selects.push('way' + feature.properties.osmid);
                    break;
                case 'Polygon':
                    selects.push('way' + feature.properties.osmid);
                    break;
                case 'MultiPolygon':
                    selects.push('relation' + feature.properties.osmid);
                    break;
                }
            }

            uri += selects.join(',');

            return uri;
        };

        var constructIdUri = function () {
            var zoom = map.getZoom();
            var center = map.getCenter();
            var lat = center.lat;
            var lon = center.lng;
            var baseUriComponent = "http://openstreetmap.us/iD/release/#";
            var idUriComponent = "id=";
            var mapUriComponent = "map=" + [zoom, lon, lat].join('/');
            // http://openstreetmap.us/iD/release/#background=Bing&id=w238383695,w238383626,&desmap=20.00/-77.02271/38.90085
            for (i in task.features) {
                var feature = task.features[i];
                if (!feature.properties.osmid) {
                    continue;
                }
                switch (feature.geometry.type) {
                case 'Point':
                    idUriComponent += "n" + feature.properties.osmid + ",";
                    break;
                case 'LineString':
                    idUriComponent += "w" + feature.properties.osmid + ",";
                    break;
                case 'Polygon':
                    idUriComponent += "w" + feature.properties.osmid + ",";
                    break;
                case 'MultiPolygon':
                    idUrlComponent += "r" + feature.properties.osmid + ",";
                    break
                }
            }
            // remove trailing comma - iD won't play ball with it
            idUriComponent = idUriComponent.replace(/,$/, "");
            var uri = baseUriComponent + [idUriComponent, mapUriComponent].join('&');
            return uri;
        };

        /*
         * A helper function to construct the URL parameters for location and difficulty
         */
        var constructUrlParameters = function (assign) {
            var params = [];
            var result = ''
            if (task.identifier) result += '/' + task.identifier;
            if (typeof near.lat === 'number' && typeof near.lon === 'number') { // this is not quite accurate but good enough for a casual check.
                params.push('lon=' + near.lon);
                params.push('lat=' + near.lat);
            }
            if (!assign) params.push('assign=0');
            // if ([1, 2, 3].indexOf(difficulty) > -1 && isChallenge) { // difficulty must be 1,2,3
            //     urlParams += 'difficulty=' + difficulty
            // }
            result += '?' + params.join('&');
            return result;
        };

        /*
         * This function initializes the leaflet map, gets the user location, and loads the first task.
         * A challenge is selected based on the user location, the URL parameter, or on the server side using the stored OSM home location.
         * elem is the div id on the page
         */
        var init = function (elem) {

            // check if the map element exists.
            if (!document.getElementById(elem)) return false;


            // initialize the map
            if (USE_SKOBBLER) {
                map = new L.skobbler.map(elem, MRConfig.mapOptions);
            } else {
                map = new L.Map(elem, MRConfig.mapOptions);

                var layers = {};

                // add each layer to the map
                for (tileLayerKey in MRConfig.tileLayers) {
                    var tileLayer = MRConfig.tileLayers[tileLayerKey];
                    var layer = new L.TileLayer(tileLayer.url, {
                    attribution: tileLayer.attribution});
                    map.addLayer(layer);
                    // add layer to control
                    layers[tileLayerKey.replace('_',' ')] = layer;
                };

                // add Layer control to the map
                L.control.layers(layers, null, {position:"topleft"}).addTo(map);

            }

            // Add both the tile layer and the task layer to the map
            map.addLayer(taskLayer);

            // Register the keyboard shortcuts
            MRManager.registerHotkeys();

            // Register AJAX error handler
            $(document).ajaxError(function (event, jqxhr, settings, exception) {
                // If there's an error, let's check to see if it's
                // a Maproulette error
                if (jqxhr.status == 555) {
                    // an OSM error was thrown
                    var osmerror = $.parseJSON(jqxhr.responseText);
                    if (osmerror.error == "ChallengeComplete") {
                        presentChallengeComplete();
                    }
                } else if (jqxhr.status == 404) {
                    // the challenge or task cannot be found - assuming the challenge is no longer active.
                    presentChallengeComplete();
                } else if (jqxhr.status === 0) {
                    // status code 0 is returned if remote control does not respond
                    toastr.error('JOSM remote control did not respond. Do you have JOSM running with Remote Control enabled?');
                }
            });

            if (this.loggedIn) {
                // check if the user passed things
                if (parseHash()) {
                    readyToEdit();
                } else {
                    selectChallenge();
                }
            } else {
                // a friendly welcome
                presentWelcomeDialog();
            }
        };

        /*
         * check if a challenge exists
         */
        var challengeExists = function (slug) {
            var status;
            var url = '/api/challenge/' + slug
            $.ajax({
                url: url,
                async: false,
                complete: function (xhr, textStatus) {
                    status = xhr.status;
                }
            });
            return status === 200;
        }

        /*
         * get a named, or random challenge
         */
        var selectChallenge = function (presentDialog) {
            // by default, present the challenge dialog after selecting the challenge.
            presentDialog = typeof presentDialog !== 'undefined' ? presentDialog : true;
            var url = "";
            // if no specific challenge is passed in,
            // check what the cookie monster has for us
            if (!challenge.slug) {
                challenge.slug = $.cookie('challenge');
            };
            // now retrieve the challenge (it will get a random one if there's no slug yet)
            retrieveChallenge();

            $.cookie('challenge', challenge.slug);

            // update the challenge detail UI elements
            $('#challenge_title').text(challenge.title);
            $('#challenge_blurb').text(challenge.blurb);

            // and move on to get the stats
            getChallengeStats();

            if (presentDialog) presentChallengeDialog();
        };

        // This retrieves a challenge - if there is already a challenge object with a slug property, it will get its details, otherwise it will retrieve a random challenge.
        var retrieveChallenge = function() {
            var url = (challenge && challenge.hasOwnProperty('slug')) ? "/api/challenge/" + challenge.slug : "/api/challenge/";
            $.ajax({
                url: url,
                async: false,
                success: function (data) {
                    challenge = data;
                }
            });
        };

        var getChallengeStats = function () {
            //now get the challenge stats
            var endpoint = '/api/challenge/' + challenge.slug + "/summary";
            $.getJSON(endpoint, function (data) {
                for (key in data) {
                    var value = parseInt(data[key]) > 10 ? 'about ' + (~~((parseInt(data[key]) + 5) / 10) * 10) : 'only a few';
                    $('#challenge_' + key).html(value).fadeIn();
                };
            });
        };

        var updateTask = function (action) {
            // if we don't have a task yet, return immediately
            if (!task) {
                return false
            }
            var payload = {
                "action": action,
                "editor": editor
            };
            $.ajax({
                url: "/api/challenge/" + challenge.slug + "/task/" + task.identifier,
                type: "PUT",
                data: payload
            });
        };

        /*
         * get a task for the current challenge
         */
        var getTask = function (assign) {
            // assign the task by default.
            assign = typeof assign !== "boolean" ? true : assign;
            // get a task
            $.ajax({
                url: '/api/challenge/' + challenge.slug + '/task' + constructUrlParameters(assign),
                async: false,
                success: function (data) {
                    task = data;
                    if (['fixed', 'alreadyfixed', 'validated', 'falsepositive', 'notanerror'].indexOf(task.status) > -1) {
                        setTimeout(function () {
                            toastr.warning('This task is already fixed, or it was marked as not an error.')
                        }, 2000);
                    }
                    //...and its geometries
                    $.ajax({
                        url: '/api/challenge/' + challenge.slug + '/task/' + task.identifier + '/geometries',
                        async: false,
                        success: function (data) {
                            task.features = data.features;
                            if (!task.hasOwnProperty('instruction') || task.instruction == null || task.instruction === '') {
                                task.instruction = challenge.instruction;
                            }
                            drawTask();
                            getChallengeStats();
                            updateHash();
                        }
                    });
                }
            });
        };

        /*
         * draw the task features onto the map canvas
         */
        var drawTask = function () {
            // clear the previous task from the layer
            taskLayer.clearLayers();

            // if we don't have a task, get one
            if (typeof task === 'undefined') return false;
            // draw all features of this task on the task layer
            for (var i = 0; i < task.features.length; i++) {
                feature = task.features[i];
                taskLayer.addData(feature);
            }
            // fit the map snugly to the task features
            map.fitBounds(taskLayer.getBounds().pad(0.2));
            // show the task text as a notification
            toastr.clear();
            toastr.info(marked(task.instruction), '', { timeOut: 0 });
            // let the user know where we are
            displayAdminArea();
            return true;
        };

        var displayAdminArea = function () {
            var mqurl = 'http://open.mapquestapi.com/nominatim/v1/reverse.php?key=Nj8oRSldMF8mjcsqp2JtTIcYHTDMDMuq&format=json&lat=' + map.getCenter().lat + '&lon=' + map.getCenter().lng;
            $.ajax({
                url: mqurl,
                jsonp: "json_callback",
                success: function (data) {
                    toastr.info(MRHelpers.mqResultToString(data.address));
                }
            });
        };

        var nextTask = function (action) {
            // make the done dialog disappear if it is there
            $('#dialog').fadeOut();
            // update the outgoing task
            if (action != undefined) {
                updateTask(action);
            }
            task = {};
            getTask();
        };

        var openTaskInJosm = function () {
            if (map.getZoom() < MRConfig.minZoomLevelForEditing) {
                toastr.warning(MRConfig.strings.msgZoomInForEdit);
                return false;
            }
            var josmUri = constructJosmUri();
            // Use the .ajax JQ method to load the JOSM link unobtrusively and alert when the JOSM plugin is not running.
            $.ajax({
                url: josmUri,
                success: function (t) {
                    if (t.indexOf('OK') === -1) {
                        toastr.error('JOSM remote control did not respond. Do you have JOSM running with Remote Control enabled?');
                    } else {
                        updateTask('editing');
                        setTimeout(confirmRemap, 4000);
                    }
                }
            });
        };

        var openTaskInId = function () {
            // this opens a new tab and focuses the browser on it.
            // We may want to consider http://stackoverflow.com/a/11389138 to
            // open a tab in the background - seems like that trick does not
            // work in all browsers.
            window.open(constructIdUri(), 'MRIdWindow');
            updateTask('editing');
            toastr.info('Your task is being loaded in iD in a separate tab. Please return here after you completed your fixes!');
            setTimeout(confirmRemap, 4000)
        };

        var presentDoneDialog = function () {
            // Right now we only support default tasks
            React.render(
                <DefaultDoneDialog />,
                document.getElementById('dialog'));
            $('#dialog').fadeIn();
        };

    var presentChallengeComplete = function(){
        React.render(
            <div>
            <p>The challenge you were working on is all done.
               Thanks for helping out!
            </p>
            <Button onClick={MRManager.presentChallengeSelectionDialog}>
              Pick another challenge</Button>
            </div>, document.getElementById('dialog'));
        $('#dialog').fadeIn();
    };

        var presentChallengeSelectionDialog = function () {
            $('controlpanel').fadeOut();
            React.render(<ChallengeSelectionDialog />, document.getElementById('dialog'));
            $('#dialog').fadeIn();
        };

    var presentChallengeHelp = function (){
        var renderedHelp = marked(challenge.help);
        React.render(
                <div>
                <h1>{challenge.title} Help</h1>
                <div className="text" dangerouslySetInnerHTML={{__html: renderedHelp}} />
                <Button onClick={closeDialog(MRManager.readyToEdit)}>OK</Button>
                </div>,
            document.getElementById('dialog'));
        $('#dialog').fadeIn();
    };

  var presentWelcomeDialog = function() {
    React.render(
        <div>
        <h1>Welcome to MapRoulette</h1>
        <p>Not sure what to map? MapRoulette knows!</p>
        <p>Whether you have a few minutes or hours to spare, MapRoulette will keep giving you useful things to do to help make OpenStreetMap better instantly.</p>
        <p>Not too experienced? There are easy challenges just for you. Or if you feel up to it, try one of the harder challenges.</p>
        <p>Whatever your skill level, have fun and thanks for trying MapRoulette!</p>
        <p><b>To get started, please sign in with your OpenStreetMap account.</b></p>
        <Button onClick={signIn}>Sign in</Button>
        </div>, document.getElementById('dialog'));
    $('#dialog').fadeIn();
  };


    var presentChallengeDialog = function(){
        if (!challenge.slug){
            presentChallengeSelectionDialog();
        };
        var renderedDescription = marked(challenge.description);
        React.render(
            <div>
            <h1>Welcome to MapRoulette!</h1>
            <p>You will be working on this challenge:</p>
            <h2>{challenge.title}</h2>
            <div dangerouslySetInnerHTML={{__html: renderedDescription}} />
            <Button onClick={MRManager.readyToEdit}>
            Let&#39;s go!
            </Button>
            <Button onClick={MRManager.presentChallengeSelectionDialog}>
            Pick another challenge</Button>
            <Button onClick={MRManager.presentChallengeHelp}>
            More Help</Button>
            </div>,
            document.getElementById('dialog'));
        $("#dialog").fadeIn();
    };

        var readyToEdit = function () {
            // Make sure we have the challenge details
            if (!challenge.title) retrieveChallenge();
            // UI preparation
            $('#dialog').fadeOut();
            $('.controlpanel').fadeIn();
            // Load a task
            task.identifier?getTask():nextTask();
        };

        var geolocateUser = function () {
            // Locate the user and define the event triggers
            map.locate({
                setView: false,
                timeout: 10000,
                maximumAge: 0
            });
            // If the location is found, let the user know, and store.
            map.on('locationfound', function (e) {
                near.lat = parseFloat(e.latlng.lat);
                near.lon = parseFloat(e.latlng.lng);
                toastr.info('We found your location. MapRoulette will try and give you tasks closer to home if they are available.');
            });
            // If the location is not found, meh.
            map.on('locationerror', function (e) {
                console.log('location not found or not permitted: ' + e.message);
            });
        };

        var confirmRemap = function () {
            presentDoneDialog();
        };

        var userPickChallenge = function (slug) {
            slug = decodeURI(slug);
            $('#dialog').fadeOut({
                complete: function () {
                    $('.controlpanel').fadeIn()
                }
            });
            challenge.slug = slug;
            selectChallenge(false);
            task = {};
            nextTask();
        };

        var userPickEditLocation = function () {
            toastr.info('Click on the map to let MapRoulette know where you want to edit.<br />' + 
                'You can use the +/- on your keyboard to increase the radius of your area.<br /><br />' + 
                'When you are satisfied with your selection, <b>Click this notification to confirm your selection</b>.<br />' + 
                'To unset your editing area, or cancel, click this dialog without making a selection.', '',  { 
                    timeOut: 0,
                    onHidden: MRManager.confirmPickingLocation});
            // remove geoJSON layer
            map.removeLayer(taskLayer);
            // set zoom level
            if (map.getZoom() > 10) map.setZoom(10, true);
            // add area on click
            map.on('click', MRManager.isPickingLocation);
            // add handlers for increasing radius
            $(document).bind('keypress.plusminus', function (e) {
                if (map.hasLayer(editArea)) {
                    if (editArea.getRadius() < MAX_EDIT_RADIUS && (e.which == 43 || e.which == 61)) { // plus
                        editArea.setRadius(editArea.getRadius() + (100 * 18 - Math.max(9, map.getZoom()))); // zoom dependent increase
                    } else if (editArea.getRadius() > 0 && (e.which == 45 || e.which == 95)) { // minus
                        editArea.setRadius(editArea.getRadius() - (100 * 18 - Math.max(9, map.getZoom()))); // zoom dependent decrease
                    }
                }
            });
        }

        var isPickingLocation = function (e) {
            var zoomDependentEditRadius = 100 * Math.pow(2, 18 - Math.max(6, map.getZoom()));
            if (map.hasLayer(editArea)) {
                zoomDependentEditRadius = editArea.getRadius();
                map.removeLayer(editArea);
            };
            editArea = new L.Circle(e.latlng, zoomDependentEditRadius)
            editArea.addTo(map);
        }

        var confirmPickingLocation = function() {
            var data = {};
            if (!editArea) {
                data ={
                    "lon" : null,
                    "lat" : null,
                    "radius" : null 
                };
                $('#msg_editarea').hide();
                toastr.clear();
                toastr.info('You cleared your designated editing area.');
            } else {
                data = {
                    "lon" : editArea.getLatLng().lng,
                    "lat" : editArea.getLatLng().lat,
                    "radius" : editArea.getRadius() 
                };
                $('#msg_editarea').show();
                toastr.clear();
                toastr.info('You have set your preferred editing location.');
            };
            storeServerSettings(data);
            if(map.hasLayer(editArea)) map.removeLayer(editArea);
            editArea = null;
            map.addLayer(taskLayer);
            map.off('click', MRHelpers.isPickingLocation);
            $(document).unbind('keypress.plusminus', false);
            getChallengeStats();
            setTimeout(MRManager.presentChallengeSelectionDialog(), 4000);
        }

        var getServerSettings = function(keys) {
            // This gets the server stored session settings for the given array of keys from /api/me
            // untested and not used yet anywhere
            $.getJSON('/api/me', function(data) {
                var out = {};
                for (var i = 0; i < keys.length; i++) {
                    if (keys[i] in data && data[keys[i]] != null) {
                        out[keys[i]] = data[keys[i]];
                    }
                };
                return out;
            });
        }

        var storeServerSettings = function(data) {
            // This stores a dict of settings on the server
            $.ajax({
                url: "/api/me",
                type: "PUT",
                contentType: "application/json",
                data: JSON.stringify(data)
            });
        }

        var registerHotkeys = function () {
            $(document).keypress(function( e ) {
                switch(e.keyCode) {
                    case 81:
                        console.log('q pressed');
                        MRManager.nextTask("falsepositive");
                        break;
                    case 87:
                        console.log('w pressed');
                        MRManager.nextTask("skipped");
                        break;
                    case 69:
                        console.log('e pressed');
                        MRManager.openTaskInId();
                        break;
                    case 82:
                        console.log('r pressed');
                        MRManager.openTaskInJosm();
                        break;
                    case 27:
                        console.log('esc pressed');
                        $('#dialog').fadeOut();
                        break;
                    default:
                        break;
                }
            });
        }

        var updateHash = function () {
            location.hash = 't=' + challenge.slug + '/' + task.identifier;
        }

        var parseHash = function () {
            if (location.hash) {
                var h = location.hash;
                if (h.indexOf('#t=') == 0) {
                    // we have a request for a specific task
                    /// looking like #c=slug/task_identifier
                    var res = h.substr(3).split('/');
                    challenge.slug = res[0];
                    task.identifier = res[1];
                    return true;
                };
                if (h.indexOf('#p=') == 0) {
                    // we have a request for location / difficulty
                    // looking like #p=1/-122.432/44.23123
                    // (difficulty/lon/lat)
                    var res = h.substr(3).split('/');
                    difficulty = res[0];
                    near.lon = res[1];
                    near.lat = res[2];
                    return true;
                }
                if (h.indexOf('#c=') == 0) {
                    // we have another command
                    switch (h.substr(3)) {
                    case 'rnd':
                        readyToEdit();
                        break;
                    default:
                        return true;
                    }
                }
                return false;
            }
        };

        return {
            init: init,
            nextTask: nextTask,
            openTaskInId: openTaskInId,
            openTaskInJosm: openTaskInJosm,
            geolocateUser: geolocateUser,
            userPickChallenge: userPickChallenge,
            userPickEditLocation: userPickEditLocation,
            isPickingLocation: isPickingLocation,
            confirmPickingLocation: confirmPickingLocation,
            readyToEdit: readyToEdit,
            presentChallengeSelectionDialog: presentChallengeSelectionDialog,
            presentChallengeHelp: presentChallengeHelp,
            registerHotkeys: registerHotkeys,
            getServerSettings: getServerSettings,
            storeServerSettings: storeServerSettings
        };
    }
    ());

// initialization
function init(elemName) {
    $('.controlpanel').fadeOut();
    MRManager.init(elemName);
}
