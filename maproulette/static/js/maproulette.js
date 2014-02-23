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
            open: {
                height: 'toggle'
            },
            close: {
                height: 'toggle'
            },
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
            onShow: function () {},
            afterShow: function () {},
            onClose: function () {},
            afterClose: function () {}
        },
        buttons: false // an array of buttons
    };
    // play a notification using options
    // the options are specific to the notification framework used.
    // currently we use noty, see http://ned.im/noty/#options
    var play = function (text, options) {
        // if an array (of lines) was passed in, join them
        if (Object.prototype.toString.call(text) === '[object Array]') {
            text = text.join('<br />');
        }
        // if no options were passed in, initialize options object
        if (!options) options = {};
        options.text = text;
        return $('.notifications').noty(options);
    };

    // clear the notification queue
    var clear = function () {
        $.noty.clearQueue();
    };

    // cancel a notification by id
    var close = function (n) {
        if (typeof n === 'noty') n.close();
    };

    return {
        play: play,
        clear: clear,
        close: close
    }
}();

var MRButtons = function () {

    var buttonTypes = {
        'fixed': 'I fixed it!',
        'skipped': 'Too difficult / Couldn\'t see',
        'falsepositive': 'It was not an error',
        'alreadyfixed': 'Someone beat me to it'
    };

    var makeButton = function (buttonType) {
        if (!(buttonType in buttonTypes)) {
            return false
        }
        return '<div class=\'button\' onClick=MRManager.nextTask(\'' + buttontype + '\') id=\'' + buttonType + '\'>' + buttonTypes[buttonType] + '</div>';
    };

    var makeButtons = function () {
        var buttonHTML = '';
        for (key in buttonTypes) {
            buttonHTML += '<div class=\'button\' onClick=MRManager.nextTask(\'' + key + '\') id=\'' + key + '\'>' + buttonTypes[key] + '</div>\n';
        }
        return buttonHTML;
    };

    return {
        makeButton: makeButton,
        makeButtons: makeButtons
    };

}();

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
        mqResultToString: mqResultToString
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
        var challenges = [];
        var challenge = {};
        var task;
        var editor;
        var near = (Q.lon && Q.lat) ? {
            'lon': parseFloat(Q.lon),
            'lat': parseFloat(Q.lat)
        } : {};
        var difficulty = parseInt(Q.difficulty);
        var taskLayer;

        // create a notifier
        notify = MRNotifier;

        // are we logged in?
        this.loggedIn = false;

        var constructJosmUri = function () {
            var bounds = map.getBounds();
            var nodes = [];
            var ways = [];
            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var uri = 'http://127.0.0.1:8111/load_and_zoom?left=' + sw.lng + '&right=' + ne.lng + '&top=' + ne.lat + '&bottom=' + sw.lat + '&new_layer=0';

            for (f in task.features) {
                var feature = task.features[f];
                if (!feature.properties.osmid) {
                    continue;
                }
                switch (feature.geometry.type) {
                case 'Point':
                    uri += '&select=node' + feature.properties.osmid;
                    break;
                case 'LineString':
                    uri += '&select=way' + feature.properties.osmid;
                    break;
                }
            }
            console.log('constructed ' + uri)
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
                }
            }
            var uri = baseUriComponent + [idUriComponent, mapUriComponent].join('&');
            console.log('constructed ' + uri);
            return uri;
        };

        /*
         * A helper function to construct the URL parameters for location and difficulty
         * if it is for a challenge, we need the difficulty as well as the location.
         */
        var constructUrlParameters = function (isChallenge) {
            var urlParams = '?';
            if (typeof near.lat === 'number' && typeof near.lon === 'number') { // this is not quite accurate but good enough for a casual check.
                urlParams += 'lon=' + near.lon + '&lat=' + near.lat + '&';
            }
            if ([1, 2, 3].indexOf(difficulty) > -1 && isChallenge) { // difficulty must be 1,2,3
                urlParams += 'difficulty=' + difficulty
            }
            return urlParams;
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
            map = new L.Map(elem, MRConfig.mapOptions);

            // and the tile layer
            var tileLayer = new L.TileLayer(MRConfig.tileUrl, {
                attribution: MRConfig.tileAttrib
            });

            // and the GeoJSON layer
            taskLayer = new L.geoJson(null, {
                onEachFeature: function (feature, layer) {
                    if (feature.properties && feature.properties.text) {
                        layer.bindPopup(feature.properties.text);
                        return layer.openPopup();
                    }
                }
            });

            // Add both the tile layer and the task layer to the map
            map.addLayer(tileLayer);
            map.addLayer(taskLayer);

            // Register the keyboard shortcuts
            MRManager.registerHotkeys();

            if (this.loggedIn) {
                // check if the user hand picked a challenge
                if (Q.challenge && challengeExists(Q.challenge)) {
                    challenge.slug = Q.challenge;
                    $.cookie('challenge', challenge.slug)
                }

                // Request a challenge
                selectChallenge();

                presentChallengeDialog();

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
        var selectChallenge = function (slug) {
            // if no specific challenge is passed in,
            // check what the cookie monster has for us
            if (!slug) {
                console.log("Setting challenge from cookie to: " + $.cookie('challenge'));
                slug = $.cookie('challenge');
            };
            // if we still don't have anything, let the server select a challenge for us.
            if (!slug) {
                console.log("Letting server select a challenge");
                url = '/api/challenge';
            } else {
                console.log("Getting challenge details for " + slug);
                url = "/api/challenge/" + slug;
            };
            $.ajax({
                url: url,
                async: false,
                success: function (data) {
                    challenge = data;
                    console.log('got challenge ' + challenge.slug);
                    // set the challenge cookie
                    $.cookie('challenge', challenge.slug);
                    // update the challenge detail UI elements
                    $('#challenge_title').text(challenge.title);
                    $('#challenge_blurb').text(challenge.blurb);
                    // and move on to get the stats
                    getChallengeStats()
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log('ajax error');
                }
            });
        };


        var getChallengeStats = function () {
            // now get the challenge stats
            console.log('getting challenge stats');
            url = '/api/challenge/' + challenge.slug + '/stats';
            challenge.stats = {};
            $.ajax({
                url: url,
                success: function (data) {
                    $.each(data, function (key, value) {
                        challenge.stats[key] = value;
                    });
                    // update the stats UI elements
                    $('#stats #total').text(challenge.stats.total);
                    $('#stats #available').text(challenge.stats.available);
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log('ajax error');
                }
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
                type: "POST",
                data: payload,
                success: function (data) {
                    console.log('task ' + task.identifier + ' updated')
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log('ajax error');
                }
            });


        };

        /*
         * get a task for the current challenge
         */
        var getTask = function () {
            if (!challenge) {
                selectChallenge();
            }
            // get a task
            $.ajax({
                url: '/api/challenge/' + challenge.slug + '/task' + constructUrlParameters(),
                async: false,
                success: function (data) {
                    task = data;
                    //...and its geometries
                    $.ajax({
                        url: '/api/challenge/' + challenge.slug + '/task/' + task.identifier + '/geometries',
                        async: false,
                        success: function (data) {
                            task.features = data.features;
                        },
                        error: function (jqXHR, textStatus, errorThrown) {
                            console.log('ajax error');
                        }
                    });
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log('ajax error');
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
            if (typeof task === 'undefined') {
                console.log('we don\'t have a task');
                return false;
            }
            // draw all features of this task on the task layer
            for (var i = 0; i < task.features.length; i++) {
                feature = task.features[i];
                taskLayer.addData(feature);
                console.log('geojson layer now has ' + taskLayer.getLayers().length + ' things.');
            }
            // fit the map snugly to the task features
            map.fitBounds(taskLayer.getBounds().pad(0.2));
            // show the task text as a notification
            notify.play(task.instruction, {
                timeout: false,
                killer: true
            });
            // let the user know where we are
            displayAdminArea();
            return true;
        };

        var displayAdminArea = function () {
            var mqurl = 'http://open.mapquestapi.com/nominatim/v1/reverse?format=json&lat=' + map.getCenter().lat + ' &lon=' + map.getCenter().lng;
            $.ajax({
                url: mqurl,
                success: function (data) {
                    notify.play(MRHelpers.mqResultToString(data.address));
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    console.log('ajax error');
                }
            });
        };

        var nextTask = function (action) {
            // make the done dialog disappear if it is there
            $('.donedialog').delay(1000).fadeOut();
            // update the outgoing task
            updateTask(action);
            getAndShowTask();
        };

        var getAndShowTask = function () {
            getTask();
            drawTask();
            getChallengeStats();
        }

        var openTaskInJosm = function () {
            if (map.getZoom() < MRConfig.minZoomLevelForEditing) {
                notify.play(MRConfig.strings.msgZoomInForEdit, {
                    type: 'warning'
                });
                return false;
            }
            var josmUri = constructJosmUri();
            // Use the .ajax JQ method to load the JOSM link unobtrusively and alert when the JOSM plugin is not running.
            $.ajax({
                url: josmUri,
                success: function (t) {
                    if (t.indexOf('OK') === -1) {
                        notify.play('JOSM remote control did not respond. Do you have JOSM running with Remote Control enabled?', {
                            type: 'error'
                        });
                    } else {
                        console.log('the data was loaded in JOSM, now waiting for callback');
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
            window.open(constructIdUri(), '_blank');
            updateTask('editing');
            notify.play('Your task is being loaded in iD in a separate tab. Please return here after you completed your fixes!');
            setTimeout(confirmRemap, 4000)
        };

        var presentDoneDialog = function () {
            var d = challenge.done_dlg;

            // if there is no done dialog info, bail
            // FIXME we should be reverting to a default
            if (typeof d === 'undefined') {
                return false
            }
            var dialogHTML = '<div class=\'text\'>' + d.text + '</div>';

            if (typeof d.buttons === 'string' && d.buttons.length > 0) {
                var buttons = d.buttons.split('|');
                for (var i = 0; i < buttons.length; i++) {
                    dialogHTML += MRButtons.makeButton(buttons[i]);
                }
            } else {
                dialogHTML += MRButtons.makeButtons();
            }
            $('.donedialog').html(dialogHTML).fadeIn();
        };

        var presentChallengeSelectionDialog = function () {
            $('controlpanel').fadeOut();
            $('.donedialog').fadeOut({
                complete: function () {
                    if (challenges.length == 0) {
                        $.ajax({
                            url: "/api/challenges",
                            success: function (data) {
                                challenges = data;
                                cancelButton = "<div class='button cancel' onclick='MRManager.readyToEdit()'>Nevermind</div>";
                                dialogHTML = "<h2>Pick a different challenge</h2>";
                                for (c in challenges) {
                                    cHTML = "<div class=\'challengeBox\'><h3>" + challenges[c].title + "</h3><p>" + challenges[c].blurb + "<div class='button' onclick=MRManager.userPickChallenge('" + challenges[c].slug + "')>Work on this challenge!</div></div>";
                                    dialogHTML += cHTML;
                                };
                                console.log(dialogHTML);
                                $('.donedialog').html(dialogHTML).fadeIn();
                            },
                            error: function (jqXHR, textStatus, errorThrown) {
                                console.log('ajax error')
                            }
                        });
                    } else {
                        $('.donedialog').html(dialogHTML).fadeIn();
                    };
                }
            });
        };

        var presentChallengeHelp = function () {
            $('.donedialog').fadeOut({
                complete: function () {
                    var OKButton = "<div class='button' onclick='MRManager.readyToEdit()'>OK</div>";
                    var helpHTML = "<h1>" + challenge.title + " Help</h1>" +
                        "<div>" + challenge.help + "</div>" + OKButton;
                    $('.donedialog').html(helpHTML).fadeIn();
                }
            });
        };

        var presentWelcomeDialog = function () {
            $('.donedialog').fadeOut();
            var OKButton = '<div class=\'button\' onclick="location.reload();location.href=\'/signin\'">Sign in</div>';
            var welcomeHTML = "<h1>Welcome to MapRoulette</h1>" + "<p>Sign in with OpenStreetMap to play MapRoulette<p>" + OKButton;
            $('.donedialog').html(welcomeHTML).fadeIn();
        };

        var presentChallengeDialog = function () {
            $('.donedialog').fadeOut({
                complete: function () {
                    var OKButton = "<div class='button' onclick='MRManager.readyToEdit()'>Let's go!</div>";
                    var helpButton = "<div class='button' onclick='MRManager.presentChallengeHelp()'>More help</div>";
                    var changeChallengeButton = "<div class='button' onclick='MRManager.presentChallengeSelectionDialog()'>Pick another challenge</div>";
                    var dialogHTML = "<h1>Welcome to MapRoulette!</h1>" +
                        "<p>You will be working on this challenge:</p>" +
                        "<h2>" + challenge.title + "</h2>" +
                        "<p>" + challenge.description + "</p>" + OKButton + helpButton + changeChallengeButton;
                    $('.donedialog').html(dialogHTML).fadeIn();
                }
            });
        };

        var readyToEdit = function () {
            console.log("Clearing the screen to edit")
            $('.donedialog').fadeOut();
            $('.controlpanel').fadeIn();
            if (!task) {
                console.log("No task. Loading one")
                getAndShowTask();
            }
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

        var userPickChallenge = function (slug) {
            $('.donedialog').fadeOut({
                complete: function () {
                    $('.controlpanel').fadeIn()
                }
            });
            console.log('user picking challenge')
            selectChallenge(slug);
            getAndShowTask();
        };

        var userPreferences = function () {
            console.log('user setting preferences');
        };

        var registerHotkeys = function () {
            $(document).bind('keypress', 'q', function () {
                MRManager.nextTask("falsepositive")
            });
            $(document).bind('keypress', 'w', function () {
                MRManager.nextTask("skipped")
            });
            $(document).bind('keypress', 'e', function () {
                MRManager.openTaskInId()
            });
            $(document).bind('keypress', 'r', function () {
                MRManager.openTaskInJosm()
            });
        }

        return {
            init: init,
            nextTask: nextTask,
            getAndShowTask: getAndShowTask,
            openTaskInId: openTaskInId,
            openTaskInJosm: openTaskInJosm,
            geolocateUser: geolocateUser,
            userPreferences: userPreferences,
            userPickChallenge: userPickChallenge,
            readyToEdit: readyToEdit,
            presentChallengeSelectionDialog: presentChallengeSelectionDialog,
            presentChallengeHelp: presentChallengeHelp,
            registerHotkeys: registerHotkeys
        };
    }
    ());

// initialization
function init(elemName) {
    $('.controlpanel').fadeOut();
    MRManager.init(elemName);
}