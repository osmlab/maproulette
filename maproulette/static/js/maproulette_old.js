(function ()
{
    var addGeoJSONLayer, ajaxErrorHandler, buttonAutoChallenge,
        buttonExitApp, buttonManualChallenge, challenge, changeMapLayer,
        clearTask, currentChallenge, currentTask, difficulty,
        drawFeatures, editor, enableKeyboardShortcuts, geojsonLayer,
        getExtent, location, makeButton, makeChallengeSelectionDlg,
        makeDlg, makeWelcomeDlg, map, markdown, mrErrorHandler,
        mr_attrib, msgMovingOnToTheNextChallenge, msgZoomInForEdit,
        nomToString, pageStartTime, revGeocode, revGeocodeOSMObj, root,
        selectedFeature, showTask, tileAttrib, tileLayer, tileUrl,
        totalFixed, totalTasks, updateChallenge, updateStats, getLocation;
    root = typeof exports !== "undefined" && exports !== null ? exports :
        this;
    markdown = new Showdown.converter();
    map = void 0;
    geojsonLayer = null;
    tileLayer = null;
    tileUrl = "http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    tileAttrib =
        '© <a href="http://openstreetmap.org">\
OpenStreetMap</a> contributors';
    currentChallenge = null;
    currentTask = null;
    selectedFeature = null;
    editor = "";
    difficulty = null;
    location = null;
    challenge = null;
    totalTasks = 0;
    totalFixed = 0;
    pageStartTime = null;
    msgMovingOnToTheNextChallenge = 'OK, moving right along...';
    msgZoomInForEdit =
        "Please zoom in a little so we don't have\nto load a huge area from the API.";
    mr_attrib =
        "<small>\n  <p>\n    thing by <a href='mailto:m@rtijn.org'>Martijn van Exel and Serge Wroclawski</a>\n  <p>\n</small>";
    buttonAutoChallenge = {
        label: "Find a new challenge",
        action: "getNewChallenge()"
    };
    buttonManualChallenge = {
        label: "Let me choose a new challenge",
        action: 'window.location.href="/challenges/'
    };
    buttonExitApp = {
        label: "Return to homepage",
        action: 'window.location.href="/"'
    };
    clearTask = function ()
    {
        /*
    # Clear all the task-related variables in between tasks
    */
        currentTask = null;
        selectedFeature = null;
        map.removeLayer(geojsonLayer);
        addGeoJSONLayer();
    };
    getExtent = function (feature)
    {
        /*
    # Takes in a JSON feature and return a Leaflet LatLngBounds
    */
        var bounds, coordinates, lat, latlon, lats, lon, lons, minlat, ne,
            sw, _i, _len, _ref;
        if(!(feature.geometry.coordinates && feature.geometry.coordinates.length >
            0))
        {
            return false;
        }
        if(feature.geometry.type === "Point")
        {
            lon = feature.geometry.coordinates[0];
            lat = feature.geometry.coordinates[1];
            latlon = new L.LatLng(lat, lon);
            bounds = new L.LatLngBounds(latlon);
            bounds.extend(latlon);
            return bounds;
        }
        else
        {
            lats = [];
            lons = [];
            _ref = feature.geometry.coordinates;
            for(_i = 0, _len = _ref.length; _i < _len; _i++)
            {
                coordinates = _ref[_i];
                lats.push(coordinates[1]);
                lons.push(coordinates[0]);
            }
            minlat = Math.min.apply(Math, lats);
            sw = new L.LatLng(Math.min.apply(Math, lats), Math.min.apply(
                Math, lons));
            ne = new L.LatLng(Math.max.apply(Math, lats), Math.max.apply(
                Math, lons));
            return new L.LatLngBounds(sw, ne);
        }
    };
    makeButton = function (label, action)
    {
        /*
    # Takes in a label and onclick action and returns a button div
    */
        var button;
        button = $('div').addClass("button");
        button.attr(
        {
            onclick: action
        });
        button.content = label;
        return button;
    };
    makeDlg = function (dlgData)
    {
        /*
    # Takes dialog box data and returns a dialog box for nextUp actions
    */
        var button, buttons, dlg, dlgButtons, dlgText, item, _i, _len, _ref;
        dlgText = dlgData.text || "";
        dlgButtons = dlgData.buttons.split('|') || [];
        dlg = $('<div></div>').addClass("dlg");
        dlg.append(markdown.makeHtml(dlgText));
        buttons = $('<div></div>').addClass("buttons");
        _ref = dlgData.buttons;
        for(_i = 0, _len = _ref.length; _i < _len; _i++)
        {
            item = _ref[_i];
            button = makeButton(item.label, item.action);
            buttons.append(button);
        }
        dlg.append(buttons);
        return dlg;
    };
    makeChallengeSelectionDlg = function (challenges)
    {
        /*
    # Takes the global challenge list and returns a dialog box for it
    */
        var c, dlg, s, _i, _len;
        dlg = $('<div></div>').addClass("dlg");
        dlg.apppend("<ul>");
        for(_i = 0, _len = challenges.length; _i < _len; _i++)
        {
            c = challenges[_i];
            s = "\"<li><a href=\"retrieveChallenge(" + c.id + ")\">" + c.title +
                "</a></li>";
            dlg.append(s);
        }
        dlg.append("</ul>");
//        dlg.append(makeButton("Close", "dlgClose()"));
        return dlg;
    };
    makeWelcomeDlg = function ()
    {
        /*
    # Makes a Welcome to MapRoulette Dialog box
    */
        var dlg;
        dlg = $('<div></div>').addClass("dlg");
        dlg.append("<h1>Welcome to MapRoulette</h1>");
        dlg.append(
            "<p>Lorem ipsum dolor sit amet, consectetur adipisicing  elit, sed do eiusmod tempor incididunt ut labore et dolore magna  aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco  laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure  dolor in reprehenderit in voluptate velit esse cillum dolore eu  fugiat nulla pariatur. Excepteur sint occaecat cupidatat non  proident, sunt in culpa qui officia deserunt mollit anim id est  laborum.</p>"
        );
//        dlg.append(makeButton("Continue without logging in", "dlgClose()"));
        return dlg;
    };

    ajaxErrorHandler = function (jqxhr, statusString, error)
    {
        /*
    # Handle AJAX errors in this function (or hand them over to
    # mrErrorHandler if appropriate
    */
        var dlg;
        switch(jqxhr.status)
        {
        case 400:
            return mrErrorHandler(error);
        default:
            dlg = makeDlg(
            {
                text: "The application has encountered a critical error: " +
                    jqxhr.status + ": " + error,
                buttons: [buttonExitApp]
            });
            $.pnotify(dlg.text);
        }
    };
    mrErrorHandler = function (errorString)
    {
        /*
    # This function takes in MapRoulette errors and handles them
    */
        var desc, dlg, error;
        error = errorString.split(':')[0];
        desc = errorString.split(':')[1].trim();
        switch(error)
        {
        case "ChallengeInactive":
            dlg = makeDlg(
            {
                text: "The current challenge is unavailable (maybe down for maintence. What should we do?",
                buttons: [buttonAutoChallenge, buttonManualChallenge]
            });
            break;
        case "ChallengeComplete":
            dlg = makeDlg(
            {
                text: "This challenge has no tasks available (maybe it's complete!). What should we do?",
                buttons: [buttonAutoChallenge, buttonManualChallenge]
            });
            break;
        default:
            dlg = makeDlg(
            {
                text: "An unhandled MapRoulette error has occured. Sorry :(",
                buttons: [buttonExitApp]
            });
        }
        $.pnotify(dlg.text);
    };
    nomToString = function (addr)
    {
        /*
    # Takes a geocode object returned from Nominatim and returns a
    # nicely formatted string
    */
        var out, county, town;
        if(!addr || !(addr.town || addr.county || addr.hamlet || addr.state || addr.country))
        {
            return "We are somewhere on earth..";
        }

        out = "We are ";

        if(addr.city != null)
        {
            out += addr.city;
        }
        else
        {
            if(addr.town != null)
            {
                town = addr.town;
            }
            else if(addr.hamlet != null)
            {
                town = addr.hamlet;
            }
            else
            {
                town = "somewhere in ";
            }

            out += town;

            if(addr.county)
            {
                if(addr.county.toLowerCase().indexOf('county') > -1)
                {
                    county = ", " + addr.county + ", ";
                }
                else
                {
                    county = ", " + addr.county + " County, ";
                }

            }
            else
            {
                county = "";
            }

            out += county;

        }

        if(addr.state)
        {
            out += addr.state + ", ";
        }

        if(addr.country)
        {
            if(addr.country.indexOf("United States") > -1)
            {
                out += "the "
            }
            out += addr.country;
        }

        out += ".";

        return out;
    };

    revGeocodeOSMObj = function (feature)
    {
        /*
    # Reverse geocodes an OSM object as a geoJSON feature
    */
        var id, mqurl, request, type;
        type = feature.properties.type;
        id = feature.properties.id;
        mqurl =
            "http://open.mapquestapi.com/nominatim/v1/reverse?format=json&osm_type=" +
            type + "@osm_id=" + id;
        request = $.ajax(
        {
            url: mqurl,
            success: function (data)
            {
                var locstr;
                locstr = nomToString(data.address);
                $.pnotify(
                {
                    title: 'Regular Notice',
                    text: locstr
                });
            },
            error: function (jqXHR, textStatus, errorThrown)
            {
                return ajaxErrorHandler(jqXHR, textStatus, errorThrown)
            }
        });
    };

    revGeocode = function ()
    {
        /*
    # Reverse geocodes the center of the (currently displayed) mapTarr
    nshi
    ore,
    Coun
    */
        var mqurl, request;
        mqurl =
            "http://open.mapquestapi.com/nominatim/v1/reverse?format=json&lat=" +
            map.getCenter().lat + " &lon=" + map.getCenter().lng;
        request = $.ajax(
        {
            url     :   mqurl,
            success :   function (data)
        {
            var locstr;
            locstr = nomToString(data.address);
            $.pnotify(
            {
                title: 'Regular Notice',
                text: locstr
            });
        },
        error: function (jqXHR, textStatus, errorThrown)
        {
            return ajaxErrorHandler(jqXHR, textStatus, errorThrown)
        }
        });
    };
    drawFeatures = function (features)
    {
        /*
    # Draw the features onto the current geojson layer. Also pulls out
    # selected features
    */
        var extent, feature, _i, _len, _results;
        _results = [];
        for(_i = 0, _len = features.length; _i < _len; _i++)
        {
            feature = features[_i];
            if(feature.properties.selected === true)
            {
                selectedFeature = feature;
                geojsonLayer.addData(feature);
            }
            extent = getExtent(selectedFeature);
            _results.push(map.fitBounds(extent));
        }
        return _results;
    };
    showTask = function ()
    {
        /*
    # Displays a task to the display and waits for the user prompt
    */
        $.ajax(
        {
            url: "/api/challenge/" + challenge + "/task/" + currentTask.id + "/geometries",
            success: function (data)
            {
                console.log('got geom for task: ' + data);
                drawFeatures(data.features);
                revGeocode();
                if(currentTask.text)
                {
                    return $.pnotify(
                    {
                        title: 'Regular Notice',
                        text: currentTask.text
                    });
                }
            },
            error: function (jqXHR, textStatus, errorThrown)
            {
                return ajaxErrorHandler(jqXHR, textStatus, errorThrown)
            }
        })
    };

    this.retrieveChallenge = function (id)
    {
        /*
    # Gets a specific challenge
    */
        var request;
        console.log(getting(challenge));
        request = $.ajax(
        {
            url: "/api/challenge/" + id,
            success: function (data)
            {
                var slug;
                slug = data.slug;
                console.log(data);
                console.log(data.slug);
                updateChallenge(slug);
                updateStats(slug);
                return getTask();
            },
            error: function (jqXHR, textStatus, errorThrown)
            {
                return ajaxErrorHandler(jqXHR, textStatus, errorThrown)
            }
        });
    };
    this.getNewChallenge = function (difficulty, near)
    {
        /*
    # Gets a challenge based on difficulty and location
    */
        var request, url;
        console.log('getting new challenge');
        if(!near)
        {
            near = "" + (map.getCenter().lng) + "|" + (map.getCenter().lat);
        }
        url = "/api/challenges?difficulty=" + difficulty + "&contains=" +
            near;
        request = $.ajax(
        {
            url: "/api/challenges?difficulty=" + difficulty + "&contains=" + near,
            success: function (data)
            {
                challenge = data[0].slug;
                console.log('we got a challenge: ' + challenge);
                console.log('updating challenge...');
                updateChallenge(challenge);
                console.log('updating challenge stats...');
                updateStats(challenge);
                console.log('getting a task...');
                return getTask(near);
            },
            error: function (jqXHR, textStatus, errorThrown)
            {
                return ajaxErrorHandler(jqXHR, textStatus, errorThrown)
            }
        });
    };

    this.getTask = function (near)
    {
        var request, url;

        if(!near)
        {
            console.log('getting task near current map center');
            near = "" + (map.getCenter().lng) + "|" + (map.getCenter().lat);
        }
        console.log('getting task near provided coordinate: ' + near);
        url = "/api/challenge/" + challenge + "/task?near=" + near;
        console.log('calling ' + url);
        request = $.ajax(
        {
            url: url,
            success: function (data)
            {
                currentTask = data;
                console.log('showing task ' + currentTask.id);
                return showTask();
            },
            error: function (jqXHR, textStatus, errorThrown)
            {
                return ajaxErrorHandler(jqXHR, textStatus, errorThrown)
            }
        });
    };
    changeMapLayer = function (layerUrl, layerAttrib)
    {
        if(layerAttrib == null)
        {
            layerAttrib = tileAttrib;
        }
        /*
    # Change the tile layer
    */
        map.removeLayer(tileLayer);
        tileLayer = new TileLayer(layerUrl,
        {
            attribution: layerAttrib
        });
        return map.addLayer(tileLayer, true);
    };
    addGeoJSONLayer = function ()
    {
        /*
    # Adds a GeoJSON layer to the map
    */
        geojsonLayer = new L.geoJson(null,
        {
            onEachFeature: function (feature, layer)
            {
                if(feature.properties && feature.properties.text)
                {
                    layer.bindPopup(feature.properties.text);
                    return layer.openPopup();
                }
            }
        });
        return map.addLayer(geojsonLayer);
    };

    this.nextUp = function (action)
    {
        var near, payload, request, task_id;
//        dlgClose();
        $.pnotify(
        {
            title: 'Regular Notice',
            text: msgMovingOnToTheNextChallenge
        });
        payload = {
            "action": action,
            "editor": editor
        };
        near = currentTask.center;
        challenge = currentChallenge.id;
        task_id = currentTask.id;
        $.ajax(
        {
            url: "/api/challenge/" + challenge + "/task/" + task_id,
            type: "POST",
            data: payload,
            success: function (data)
            {
                return setDelay(1, function ()
                {
                    clearTask();
                    return getTask(near);
                });
            },
            error: function (jqXHR, textStatus, errorThrown)
            {
                return ajaxErrorHandler(jqXHR, textStatus, errorThrown)
            }
        });
    };

    this.openIn = function (e)
    {
        var JOSMurl, PotlatchURL, bounds, id, loc, ne, selectedFeatureId,
            selectedFeatureType, sw;
        editor = e;
        if(map.getZoom() < 14)
        {
            msg(msgZoomInForEdit, 3);
            return false;
        }
        bounds = map.getBounds();
        sw = bounds.getSouthWest();
        ne = bounds.getNorthEast();
        selectedFeatureId = selectedFeature.properties.id;
        selectedFeatureType = selectedFeature.properties.type;
        if(editor === "josm")
        {
            JOSMurl = "http://127.0.0.1:8111/load_and_zoom?left=" + sw.lng +
                "&right=" + ne.lng + "&top=" + ne.lat + "&bottom=" + sw.lat +
                "&new_layer=0&select=" + selectedFeaturetype +
                selectedFeatureId;
            return $.ajax(
            {
                url: JOSMurl,
                success: function (t)
                {
                    if(t.status === 200)
                    {
                        return setTimeout(confirmMapped, 4000);
                    }
                    else
                    {
                        $.pnotify(
                        {
                            text: "JOSM remote control did not respond. Do you have JOSM running?"
                        });
                    }
                }
            });
        }
        else if(editor === "potlatch")
        {
            PotlatchURL =
                "http://www.openstreetmap.org/edit?editor=potlatch2&bbox=" +
                map.getBounds().toBBoxString();
            window.open(PotlatchURL);
            return setTimeout(confirmMapped, 4000);
        }
        else if(editor === "id")
        {
            if(selectedFeatureType === "node")
            {
                id = "n" + selectedFeatureId;
            }
            else if(selectedFeatureType === "way")
            {
                id = "w" + selectedFeatureId;
            }
            loc = "" + (map.getZoom()) + "/" + (map.getCenter().lng) + "/" +
                (map.getCenter().lat);
            window.open("http://geowiki.com/iD/#id=" + id + "&map=" + loc);
            return confirmMapped();
        }
    };
    this.confirmMapped = function ()
    {
        /*
    # Show the mapping confirmation dialog box
    */
        var editorText;
        if(editor === 'josm')
        {
            editorText = 'JOSM';
        }
        else if(editor === 'potlatch')
        {
            editorText = 'Potlatch';
        }
        else if(editor === 'id')
        {
            editorText = 'iD';
        }
        $.pnotify(currentChallenge.doneDlg);
    };

    this.showHelp = function ()
    {
        /*
    # Show the about window
    */
        $.pnotify("" + currentChallenge.help + "\n<p>" + mr_attrib +
            "</p>",
            0);
    };
    updateStats = function (challenge)
    {
        /*
    # Get the stats for the challenge and display the count of remaining
    # tasks
    */
        var request;
        request = $.ajax(
        {
            url     :   "/api/challenge/" + challenge + "/stats",
            success :   function (data)
        {
            var remaining;
            remaining = data.total - data.done;
            return $("#counter").text(remaining);
        },
        error: function (jqXHR, textStatus, errorThrown)
        {
            return ajaxErrorHandler(jqXHR, textStatus, errorThrown)
        }
        });
    };
    updateChallenge = function (challenge)
    {
        /*
    # Use the current challenge metadata to fill in the web page
    */
        var request;
        console.log('updating challenge');
        request = $.ajax(
        {
            url     :   "/api/challenge/" + challenge,
            success :   function (data)
            {
                var tileURL;
                currentChallenge = data;
                $('#challengeDetails').text(currentChallenge.name);
                if((data.tileurl != null) && data.tileurl !== tileURL)
                {
                    tileURL = data.tileurl;
                    if(data.tileattribution != null)
                    {
                        tileAttrib = data.tileasttribution;
                    }
                    changeMapLayer(tileURL, tileAttrib);
                }
                currentChallenge.help = markdown.makeHtml(currentChallenge.help);
                currentChallenge.done_dlg = makeDlg(currentChallenge.done_dlg);
            },
            error   :    function (jqXHR, textStatus, errorThrown)
            {
                ajaxErrorHandler(jqXHR, textStatus, errorThrown)
            }
        });
    };
    enableKeyboardShortcuts = function ()
    {
        /*
    # Enables and sets the keyboard shortcuts
    */
        return $(document).bind("keydown", function (e)
        {
            var key;
            key = String.fromCharCode(e);
            switch(key.which)
            {
            case "q":
                return nextUp("falsepositive");
            case "w":
                return nextUp("skip");
            case "e":
                return openIn('josm');
            case "r":
                return openIn('potlatch');
            case "i":
                return openIn('id');
            }
        });
    };

    this.getChallenge = function ()
    {
        // get preference overrides from the URL parameters
        challenge = $(document).getUrlParam("challenge");
        difficulty = $(document).getUrlParam("difficulty");
        near = $(document).getUrlParam("near");
        // if a challenge is passed in, use that
        if(challenge != null)
        {
            updateChallenge(challenge);
            updateStats(challenge);
            getTask(near);
            // otherwise, assign one.
        }
        else
        {
            if(!difficulty)
            {
                difficulty = 1;
            }
            if(!near)
            {
                near = "" + (map.getCenter().lng) + "|" + (map.getCenter().lat);
            }
            getNewChallenge(difficulty, near);
        }
    }

    this.init = function ()
    {
        var near;
        var options = {
            center: new L.LatLng(40, -90),
            zoom: 17
        };
        // Set up the Leaflet map
        map = new L.Map("map", options);
        tileLayer = new L.TileLayer(tileUrl,
        {
            attribution: tileAttrib
        });
        // Locate the user and define the event triggers
        map.locate(
        {
            setView: true,
            timeout: 1000, // this may be too short but we don't want the users to wait too much
            maximumAge: 0
        });
        map.on('locationfound', function (e)
        {
            console.log('location found: ' + e);
//            getChallenge()
        });
        map.on('locationerror', function (e)
        {
            console.log('location not found: ' + e.message);
            $.pnotify('Location not found...');
            getChallenge();
        });
        map.addLayer(tileLayer);
        // Add the geoJSON layer to the map
        addGeoJSONLayer();
        // Enable the keyboard shortcuts
        enableKeyboardShortcuts();
    };
})();
