###
# This file contains all the MapRoulette client/javascript code
###
root = exports ? this

# Make the Markdown client converter
markdown = new Showdown.converter()

# Map variables
map = undefined
geojsonLayer = null
tileLayer = null

# Challenge related attributes
tileUrl = "http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
tileAttrib = '© <a href="http://openstreetmap.org">OpenStreetMap</a> contributors'

# Task specific features
currentChallenge = null
currentTask = null
selectedFeature = null

# User variables
loggedIn = false
editor = ""
difficulty = null
location = null
challenge = null

# User variables for the future
totalTasks = 0
totalFixed = 0
pageStartTime = null

# Static strings
msgMovingOnToTheNextChallenge = 'OK, moving right along...'
msgZoomInForEdit = """Please zoom in a little so we don't have to load a huge area from the API."""
mr_attrib = """
<small>
  <p>
    thing by <a href='mailto:m@rtijn.org'>Martijn van Exel and Serge Wroclawski</a>
  <p>
</small>"""

setDelay = (seconds, func) ->
  ###
  # Wraps setTimeout to make it easiet to write in Coffeescript
  ###
  # setTimeout takes miliseconds, so we multiply them by 1000
  setTimeout func, seconds * 1000

jQuery.fn.extend
  ###
  # Returns get parameters.
  #
  # If the desired param does not exist, null will be returned
  #
  # To get the document params:
  # @example value = $(document).getUrlParam("paramName");
  #
  # To get the params of a html-attribut (uses src attribute)
  # @example value = $('#imgLink').getUrlParam("paramName");
  ###
  # Taken from https://gist.github.com/thorn/2775179
  getUrlParam: (strParamName) ->
    strParamName = escape(unescape(strParamName))

    if $(this).attr("nodeName") is "#document"
      if window.location.search.search(strParamName) > -1
        qString = window.location.search.substr(1,window.location.search.length).split("&")
    else if $(this).attr("src") isnt "undefined"
      strHref = $(this).attr("src")
      if strHref.indexOf("?") > -1
        strQueryString = strHref.substr(strHref.indexOf("?") + 1)
        qString = strQueryString.split("&")
    else if $(this).attr("href") isnt "undefined"
      strHref = $(this).attr("href")
      if strHref.indexOf("?") > -1
        strQueryString = strHref.substr(strHref.indexOf("?") + 1)
        qString = strQueryString.split("&")
    else
      return null

    return null unless qString

    returnVal = (query.split("=")[1] for query in qString when escape(unescape(query.split("=")[0])) is strParamName)

    if returnVal.lenght is 0
      null
    else if returnVal.lenght is 1
      returnVal[0]
    else
      returnVal

clearTask = ->
  ###
  # Clear all the task-related variables in between tasks
  ###
  currentTask = null
  selectedFeature = null
  # Remove and re-add the geojson layer (since we can't clear it)
  map.removeLayer(geojsonLayer)
  addGeoJSONLayer()

getExtent = (feature) ->
  ###
  # Takes in a JSON feature and return a Leaflet LatLngBounds
  ###
  return false unless (feature.geometry.coordinates and
    feature.geometry.coordinates.length > 0)
  if feature.geometry.type is "Point"
    # This function is pointless for a point, but we'll support it anyway
    lon = feature.geometry.coordinates[0]
    lat = feature.geometry.coordinates[1]
    latlon = new L.LatLng(lat, lon)
    bounds = new L.LatLngBounds(latlon)
    bounds.extend(latlon)
    bounds
  else
    lats = []
    lons = []
    for coordinates in feature.geometry.coordinates
      lats.push coordinates[1]
      lons.push coordinates[0]
    minlat = Math.min.apply(Math, lats)
    sw = new L.LatLng(Math.min.apply(Math, lats), Math.min.apply(Math, lons))
    ne = new L.LatLng(Math.max.apply(Math, lats), Math.max.apply(Math, lons))
    new L.LatLngBounds(sw, ne)

@msgClose = ->
  ###
  # Close the msg box
  ###
  $("#msgBox").fadeOut()

msg = (html) ->
  ###
  # Display a msg (html) in the msgbox. Must be closed with msgClose()
  ###
  $("#msgBox").html(html).fadeIn()
  $("#msgBox").css "display", "block"

msgTaskText = ->
  ###
  # Display the current task text in the msgbox
  ###
  msg currentTask.text if currentTask.text

makeDlg = (dlgData) ->
  ###
  # Takes dialog box data and returns a dialog box for nextUp actions
  ###
  dlg = $('<div></div>').addClass("dlg")
  dlg.append(markdown.makeHtml(dlgData.text))
  buttons = $('<div></div>').addClass("buttons")
  for item in dlgData.buttons
    button = $('div').addClass("button")
    button.attr {onclick: "#{item.action}"}
    button.content(item.label)
    buttons.append(button)
  dlg.append(buttons)
  return dlg

dlgOpen = (h) ->
  ###
  #  Display the data (html) in a dialog box. Must be closed with dlgClose()
  ###
  $("#dlgBox").html(h).fadeIn()
  $("#dlgBox").css "display", "block"

@dlgClose = ->
  ###
  # Closes the dialog box
  ###
  $("#dlgBox").fadeOut()

nomToString = (addr) ->
  ###
  # Takes a geocode object returned from Nominatim and returns a
  # nicely formatted string
  ###
  str = ""
  # If the address in in a city, we don't need the county. If it's a
  # town or smaller, display the locality, county
  if addr.city?
    locality = addr.city
  else
    # Let's try to get the name of the local town/hamlet
    if addr.town?
      town = addr.town
    else if addr.hamlet?
      town = addr.hamlet
    else
      town = "Somewhere in"
    if addr.county?
      if addr.county.toLowerCase().indexOf('county') > -1
        county = ", #{addr.county}"
      else
        county = ", #{addr.county} County"
    else
      county = ""
    locality = "#{addr.town} #{county}"
  # Now we look for the state, or the nation
  if addr.state?
    "#{locality}, #{addr.state}"
  else
    if addr.country?
      "#{locality}, #{addr.country}"
    else
      "Somewhere on Earth"

revGeocodeOSMObj = (feature) ->
  ###
  # Reverse geocodes an OSM object as a geoJSON feature
  ###
  # The Nominatim documents say reverse geocoding an object is
  # preferable to a location, so this function should be used instead
  # of revGeocode
  type = feature.properties.type
  id = feature.properties.id
  mqurl = "http://open.mapquestapi.com/nominatim/v1/reverse?format=json&osm_type=#{type}@osm_id=#{id}"
  msgClose()
  $.getJSON mqurl, (data) ->
    locstr = nomToString(data.address)
    msg locstr

revGeocode = ->
  ###
  # Reverse geocodes the center of the (currently displayed) map
  ###
  mqurl = "http://open.mapquestapi.com/nominatim/v1/reverse?format=json&lat=" + map.getCenter().lat + " &lon=" + map.getCenter().lng
  #close any notifications that are still hanging out on the page.
  msgClose()
  # this next bit fires the RGC request and parses the result in a
  # decent way, but it looks really ugly.
  $.getJSON mqurl, (data) ->
    locstr = nomToString(data.address)
    # display a message saying where we are in the world
    msg locstr

drawFeatures = (features) ->
  ###
  # Draw the features onto the current geojson layer. Also pulls out
  # selected features
  ###
  for feature in features
    if feature.properties.selected is true
        selectedFeature = feature
      geojsonLayer.addData feature
    extent = getExtent(selectedFeature)
    map.fitBounds(extent)

showTask = (task) ->
  ###
  # Displays a task to the display and waits for the user prompt
  ###
  drawFeatures(task.features)
  revGeocode()
  setDelay 3, msgClose()
  msgTaskText()

getChallenge = (id) ->
  ###
  # Gets a specific challenge
  ###
  $.getJSON "/api/c/challenges/#{id}", (data) ->
    challenge = data
    updateChallenge(challenge)
    updateStats(challenge)
    getTask()

getNewChallenge = (difficulty, near) ->
  ###
  # Gets a challenge based on difficulty and location
  ###
  near = "#{map.getCenter().lng}|#{map.getCenter().lat}" if not near
  url = "/api/c/challenges?difficulty=#{difficulty}&contains=#{near}"
  $.getJSON url, (data) ->
    challenge = data.challenges[0]
    updateChallenge(challenge)
    updateStats(challenge)
    getTask(near)

@getTask = (near = null) ->
  ###
  # Gets another task from the current challenge, close to the
  # location (if supplied)
  ###
  near = "#{map.getCenter().lng}|#{map.getCenter().lat}" if not near
  url = "/api/c/challenges/#{challenge}/tasks?near=#{near}"
  $.getJSON url, (data) ->
    currentTask = data
    currentTask.startTime = new Date().getTime()
    showTask(data)

changeMapLayer = (layerUrl, layerAttrib = tileAttrib) ->
  ###
  # Change the tile layer
  ###
  map.removeLayer(tileLayer)
  tileLayer = new TileLayer(layerUrl, attribution: layerAttrib)
  # The second argument adds the layer at the bottom
  map.addLayer(tileLayer, true)

addGeoJSONLayer = ->
  ###
  # Adds a GeoJSON layer to the map
  ###
  geojsonLayer = new L.geoJson(null, {
    # We need an onEachFeature function to create markers
    onEachFeature: (feature, layer) ->
      if feature.properties and feature.properties.text
        layer.bindPopup(feature.properties.text)
        layer.openPopup()})
  map.addLayer geojsonLayer

@nextUp = (action) ->
  ###
  # Display a message that we're moving on to the next error, store
  # the result of the confirmation dialog in the database, and load
  # the next challenge
  ###
  # This should be harmless if the dialog box is already closed
  dlgClose()

  if not loggedIn
    window.location.pathname = '/oauth/authorize'

  msg msgMovingOnToTheNextChallenge
  setDelay 1, msgClose()
  payload = {
      "action": action,
      "editor": editor,
      "startTime": currentTask.startTime,
      "endTime": new Date().getTime() }
  near = currentTask.center
  challenge = currentChallenge.id
  task_id = currentTask.id
  $.post "/c/#{challenge}/task/#{task_id}", payload, ->
    setDelay 1, ->
      clearTask()
      getTask(near)

@openIn = (e) ->
  ###
  # Open the currently displayed OSM objects in the selected editor (e)
  ###
  if not loggedIn
    window.location.pathname = '/oauth/authorize'

  editor = e
  if map.getZoom() < 14
    msg msgZoomInForEdit, 3
    return false
  bounds = map.getBounds()
  sw = bounds.getSouthWest()
  ne = bounds.getNorthEast()
  selectedFeatureId = selectedFeature.properties.id
  selectedFeatureType = selectedFeature.properties.type
  if editor is "josm"
    JOSMurl =  "http://127.0.0.1:8111/load_and_zoom?left=#{sw.lng}&right=#{ne.lng}&top=#{ne.lat}&bottom=#{sw.lat}&new_layer=0&select=#{selectedFeaturetype}#{selectedFeatureId}"
    # Use the .ajax JQ method to load the JOSM link unobtrusively and
    # alert when the JOSM plugin is not running.
    $.ajax
      url: JOSMurl
      complete: (t) ->
        if t.status is 200
          setTimeout confirmMapped, 4000
        else
          msg "JOSM remote control did not respond (" + t.status + "). Do you have JOSM running?", 2

  else if editor is "potlatch"
    PotlatchURL = "http://www.openstreetmap.org/edit?editor=potlatch2&bbox=" + map.getBounds().toBBoxString()
    window.open PotlatchURL
    setTimeout confirmMapped, 4000
  else if editor is "id"
    if selectedFeatureType == "node"
      id = "n#{selectedFeatureId}"
    else if selectedFeatureType == "way"
      id = "w#{selectedFeatureId}"
    # Sorry, no relation support in iD (yet?)
    loc = "#{map.getZoom()}/#{map.getCenter().lng}/#{map.getCenter().lat}"
    window.open "http://geowiki.com/iD/#id=#{id}&map=#{loc}"
    confirmMapped()

@confirmMapped = () ->
  ###
  # Show the mapping confirmation dialog box
  ###
  if editor == 'josm'
    editorText = 'JOSM'
  else if editor == 'potlatch'
    editorText = 'Potlatch'
  else if editor == 'id'
    editorText = 'iD'

  dlgOpen(currentChallenge.doneDlg)

@showHelp = ->
  ###
  # Show the about window
  ###
  dlgOpen """#{currentChallenge.help}
  <p>#{mr_attrib}</p>
  <p><div class='button' onClick="dlgClose()">OK</div></p>""", 0

updateStats = (challenge) ->
  ###
  # Get the stats for the challenge and display the count of remaining
  # tasks
  ###
  $.getJSON "/api/c/challenges/#{challenge}/stats", (data) ->
    remaining = data.stats.total - data.stats.done
    $("#counter").text remaining

updateChallenge = (challenge) ->
  ###
  # Use the current challenge metadata to fill in the web page
  ###
  $.getJSON "/api/c/challenges/#{challenge}", (data) ->
    currentChallenge = data.challenge
    $('#challengeDetails').text currentChallenge.name
    if data.tileurl? and data.tileurl != tileURL
      tileURL = data.tileurl
      tileAttrib = data.tileasttribution if data.tileattribution?
      changeMapLayer(tileURL, tileAttrib)
    currentChallenge.help = markdown.makeHtml(currentChallenge.help)
    currentChallenge.doneDlg = makeDlg(currentChallenge.doneDlg)


enableKeyboardShortcuts = ->
  ###
  # Enables and sets the keyboard shortcuts
  ###
  $(document).bind "keydown", (e) ->
    key = String.fromCharCode(e)
    switch key.which
      when "q" then nextUp "falsepositive"
      when "w" then nextUp "skip"
      when "e" then openIn('josm')
      when "r" then openIn('potlatch')
      when "i" then openIn('id')

@init = (isLoggedIn) ->
  ###
  # Find a challenge and set the map up
  ###
  # First create the map
  map = new L.Map "map"
  map.attributionControl.setPrefix('')
  tileLayer = new L.TileLayer(tileUrl, attribution: tileAttrib)
  map.setView new L.LatLng(40.0, -90.0), 17
  map.addLayer tileLayer
  addGeoJSONLayer()
  enableKeyboardShortcuts()

  # Remember whether user is logged in
  loggedIn = isLoggedIn

  # Try to grab parameters from the url
  challenge = $(document).getUrlParam("challenge")
  difficulty = $(document).getUrlParam("difficulty")
  near = $(document).getUrlParam("near")
  # Or try to load them from user preferences
  #
  # INSERT CODE PERFERENCE LOADING CODE HERE
  #
  #
  if challenge?
    updateChallenge(challenge)
    updateStats(challenge)
    getTask(near)
  else
    if not difficulty
      difficulty = 1
    if not near
      near = "#{map.getCenter().lng}|#{map.getCenter().lat}"
    getNewChallenge(difficulty, near)
