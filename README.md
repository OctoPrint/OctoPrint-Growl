**⚠ Up for adoption! ⚠**

I have my hands way too full with OctoPrint's maintenance to give this plugin the attention it needs. Hence I'm looking for a new maintainer to adopt it. [Please get in touch here](https://github.com/OctoPrint/OctoPrint-Growl/issues/7).

---

# Growl plugin for OctoPrint

![Growl plugin: Settings dialog with discovered local Growl instances](http://i.imgur.com/glZq5zJl.png)

![Growl plugin: Example notification](http://i.imgur.com/cqYpfR4l.png)

The Growl plugin for OctoPrint allows to send notifications about certain printing events to a Growl instance on your
local network. Right now it sends notifications for the following events:
 
  * Printjob started
  * Printjob done
  * File uploaded (optional)
  * Timelapse done (optional)
 
Please note that it's a work in progress.

## Setup

Install the plugin like you would install any regular Python package from source:

    pip install https://github.com/OctoPrint/OctoPrint-Growl/archive/master.zip
    
Make sure you use the same Python environment that you installed OctoPrint under, otherwise the plugin
won't be able to satisfy its dependencies.

Restart OctoPrint. `octoprint.log` should show you that the plugin was successfully found and loaded:

    2014-09-18 17:49:21,500 - octoprint.plugin.core - INFO - Loading plugins from ... and installed plugin packages...
    2014-09-18 17:49:21,611 - octoprint.plugin.core - INFO - Found 2 plugin(s): Growl (0.1.0), Discovery (0.1)

## Configuration

You'll have to configure the host your Growl service is running on (which is probably not the same machine that 
your OctoPrint installation is running on), the port it is listening on and - if you secured your growl instance against
notifications from the network with a password - also the password needed to connect to it.

You can do all this via the settings dialog under "Plugins > Growl". If you have your OctoPrint installation's 
[bundled discovery plugin](https://github.com/foosel/OctoPrint/wiki/Plugin:-Discovery) also 
[configured with pybonjour support](https://github.com/foosel/OctoPrint/wiki/Plugin:-Discovery#installing-pybonjour) 
you'll also be able to see all the Growl instances on your local network that OctoPrint was able to discover there.

By default only the notifications for "Printjob started" and "Printjob done" are enabled. If you also want to get 
notification about the other events, you'll have to **tell Growl**. OctoPrint will send them all, but your local Growl
instance needs to be told to also display them. You can do this in the configuration of your Growl service. For example,
this is how it looks in [Growl for Windows](http://www.growlforwindows.com/gfw/):

![Growl Plugin: Example of granular notification configuration in Growl for Windows](http://i.imgur.com/Z0wJy8Bl.png)

