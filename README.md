Welcome to MapRoulette, the powerful & popular bug fixing tool (or is it a game?) for OpenStreetMap.

This README deals with development related topics only. If you are interested in contributing to OpenStreetMap by fixing some bugs through MapRoulette, just head over to [the MapRoulette web site](http://maproulette.org) and get started - it should be pretty self explanatory.

That said, read on if you want to contribute to MapRoulette development and are ready to deploy your local instance.

## Contributing

Please fork the project and submit pull requests on the `develop` branch.

See the code style conventions at https://github.com/osmlab/maproulette/wiki/Code-style-conventions

### Frameworks used

MapRoulette relies heavily on the lightweight Flask web application framework, and some of its extensions, notably Flask-OAuth, Flask-RESTful, Flask-Script, Flask-Runner and Flask-SQLAlchemy. For working with geospatial data, MapRoulette relies on GeoAlchemy2 and Shapely.

## Deploying MapRoulette

If you want to deploy your own live MapRoulette server, see the documentation [here](https://github.com/osmlab/maproulette/wiki/Maproulette-Instance-Quickstart-Guide).

If you want to set up MapRoulette locally for testing and development, and you want to benefit from the built-in debugging features of Flask, follow [these](https://github.com/osmlab/maproulette/wiki/Run-A-MapRoulette-Development-Server-Locally) steps.

## Creating new Challenges
Ceating and maintaining a good challenge is a little more complex than just pushing a button. It's not too difficult though. For a gentle introduction, please see [this workshop at SOTM EU](http://sotm-eu.org/en/slots/39) and [these slides](https://docs.google.com/presentation/d/1bl0WJ3iBjMH0AwTsOPu8sHeaInd1w-KXk_QXaEFSVFo/edit?usp=sharing) to get started.

## Contact

Bug and feature requests are best left as an issue right here on Github. For other things, contact maproulette@maproulette.org