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
tileAttrib = '© <a href="http://openstreetmap.org">
OpenStreetMap</a> contributors'

# Task specific features
currentChallenge = null
currentTask = null
selectedFeature = null

# User variables
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
msgZoomInForEdit = """Please zoom in a little so we don't have
to load a huge area from the API."""
mr_attrib = """
<small>
  <p>
    thing by <a href='mailto:m@rtijn.org'>Martijn van Exel and Serge Wroclawski</a>
  <p>
</small>"""

# Button data for use in error dialogs
buttonAutoChallenge = {
  label: "Find a new challenge",
  action: "getNewChallenge()"}

buttonManualChallenge = {
  label: "Let me choose a new challenge",
  action: 'window.location.href="/challenges/'}

buttonExitApp = {
  label: "Return to homepage"
  action: 'window.location.href="/"'}

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

makeButton = (label, action) ->
  ###
  # Takes in a label and onclick action and returns a button div
  ###
  button = $('div').addClass("button")
  button.attr {onclick: action}
  button.content = label
  return button

makeDlg = (dlgData) ->
  ###
  # Takes dialog box data and returns a dialog box for nextUp actions
  ###
  dlg = $('<div></div>').addClass("dlg")
  dlg.append(markdown.makeHtml(dlgData.text))
  buttons = $('<div></div>').addClass("buttons")
  for item in dlgData.buttons
    button = makeButton(item.label, item.action)
    buttons.append(button)
  dlg.append(buttons)
  return dlg

makeChallengeSelectionDlg = (challenges) ->
  ###
  # Takes the global challenge list and returns a dialog box for it
  ###
  dlg = $('<div></div>').addClass("dlg")
  dlg.apppend("<ul>")
  for c in challenges
    s = """"<li><a href="getChallenge(#{c.id})">#{c.title}</a></li>"""
    dlg.append(s)
  dlg.append("</ul>")
  dlg.append(makeButton("Close", "dlgClose()"))
  return dlg

makeWelcomeDlg = () ->
  ###
  # Makes a Welcome to MapRoulette Dialog box
  ###
  dlg = $('<div></div>').addClass("dlg")
  dlg.append("<h1>Welcome to MapRoulette</h1>")
  dlg.append("<p>Lorem ipsum dolor sit amet, consectetur adipisicing
  elit, sed do eiusmod tempor incididunt ut labore et dolore magna
  aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco
  laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure
  dolor in reprehenderit in voluptate velit esse cillum dolore eu
  fugiat nulla pariatur. Excepteur sint occaecat cupidatat non
  proident, sunt in culpa qui officia deserunt mollit anim id est
  laborum.</p>")
  dlg.append(makeButton("Continue without logging in", "dlgClose()"))
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

ajaxErrorHandler = ( jqxhr, statusString, error) ->
  ###
  # Handle AJAX errors in this function (or hand them over to
  # mrErrorHandler if appropriate
  ###
  switch jqxhr.status
    when 400
      # We treat 400 errors with mrErrorHandler
      mrErrorHandler(error)
    else
      # We aught to handle more errors (such as timeouts and other
      # errors For now, we will have to assume that this error is
      # critical and exit the application
      dlg = makeDlg({
        text: "The application has encountered a critical error: #{jqxhr.status}: #{error}",
        buttons: [buttonExitApp]})
      dlgOpen(dlg)

mrErrorHandler = (errorString) ->
  ###
  # This function takes in MapRoulette errors and handles them
  ###
  error = errorString.split(':')[0]
  desc = errorString.split(':')[1].trim()
  switch error
    when "ChallengeInactive"
      dlg = makeDlg({
        text: "The current challenge is unavailable (maybe down for maintence. What should we do?",
        buttons: [buttonAutoChallenge, buttonManualChallenge]})
    when "ChallengeComplete"
      dlg = makeDlg({
        text: "This challenge has no tasks available (maybe it's complete!). What should we do?",
        buttons: [buttonAutoChallenge, buttonManualChallenge]})
    else
      dlg = makeDlg({
        text: "An unhandled MapRoulette error has occured. Sorry :(",
        buttons: [buttonExitApp]})
  dlgOpen(dlg)

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
  request = $.ajax {url: mqurl}
  request.success (data) ->
    locstr = nomToString(data.address)
    msg locstr
  request.fail(ajaxErrorHandler)

revGeocode = ->
  ###
  # Reverse geocodes the center of the (currently displayed) map
  ###
  mqurl = "http://open.mapquestapi.com/nominatim/v1/reverse?format=json&lat=" + map.getCenter().lat + " &lon=" + map.getCenter().lng
  #close any notifications that are still hanging out on the page.
  msgClose()
  # this next bit fires the RGC request and parses the result in a
  # decent way, but it looks really ugly.
  request = $.ajax {url: mqurl}
  request.done (data) ->
    locstr = nomToString(data.address)
    # display a message saying where we are in the world
    msg locstr
  request.fail (ajaxErrorHandler)

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
  drawFeatures(task.manifest)
  revGeocode()
  setDelay 3, msgClose()
  msgTaskText()

@getChallenge = (id) ->
  ###
  # Gets a specific challenge
  ###
  request = $.ajax {url: "/api/c/challenges/#{id}"}
  request.done (data) ->
    challenge = data
    updateChallenge(challenge)
    updateStats(challenge)
    getTask()
  request.fail (ajaxErrorHandler)

@getNewChallenge = (difficulty, near) ->
  ###
  # Gets a challenge based on difficulty and location
  ###
  near = "#{map.getCenter().lng}|#{map.getCenter().lat}" if not near
  url = "/api/c/challenges?difficulty=#{difficulty}&contains=#{near}"
  request = $.ajax {url: "/api/c/challenges?difficulty=#{difficulty}&contains=#{near}"}
  request.done (data) ->
    challenge = data.challenges[0]
    updateChallenge(challenge)
    updateStats(challenge)
    getTask(near)
  request.fail (ajaxErrorHandler)


@getTask = (near = null) ->
  ###
  # Gets another task from the current challenge, close to the
  # location (if supplied)
  ###
  near = "#{map.getCenter().lng}|#{map.getCenter().lat}" if not near
  url = "/api/c/challenges/#{challenge}/tasks?near=#{near}"
  request = $.ajax {url: url}
  request.success (data) ->
    currentTask = data.tasks[0]
    showTask(currentTask)
  request.fail (jqXHR, textStatus, errorThrown) ->
    ajaxErrorHandler(jqXHR, textStatus, errorThrown)

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

  msg msgMovingOnToTheNextChallenge
  setDelay 1, msgClose()
  payload = {
    "action": action,
    "editor": editor}
  near = currentTask.center
  challenge = currentChallenge.id
  task_id = currentTask.id
  request = $.ajax {
    url: "/c/#{challenge}/task/#{task_id}",
    type: "POST",
    data: payload}
  request.done (data) ->
    setDelay(1, ->
      clearTask()
      getTask(near))
  request.fail (ajaxErrorHandler)

@openIn = (e) ->
  ###
  # Open the currently displayed OSM objects in the selected editor (e)
  ###
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
  request = $.ajax {url: "/api/c/challenges/#{challenge}/stats"}
  request.done (data) ->
    remaining = data.stats.total - data.stats.done
    $("#counter").text remaining
  request.fail (ajaxErrorHandler)

updateChallenge = (challenge) ->
  ###
  # Use the current challenge metadata to fill in the web page
  ###
  request = $.ajax {url: "/api/c/challenges/#{challenge}"}
  request.done (data) ->
    currentChallenge = data.challenge
    $('#challengeDetails').text currentChallenge.name
    if data.tileurl? and data.tileurl != tileURL
      tileURL = data.tileurl
      tileAttrib = data.tileasttribution if data.tileattribution?
      changeMapLayer(tileURL, tileAttrib)
    currentChallenge.help = markdown.makeHtml(currentChallenge.help)
    currentChallenge.doneDlg = makeDlg(currentChallenge.doneDlg)
  request.fail (ajaxErrorHandler)

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

@init = ->
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

