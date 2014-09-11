# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import flask
import logging

import octoprint.plugin
import octoprint.events

default_settings = {
	"hostname": None,
	"port": None,
	"password": None,
}
s = octoprint.plugin.plugin_settings("discovery", defaults=default_settings)

class GrowlPlugin(octoprint.plugin.EventHandlerPlugin,
                  octoprint.plugin.StartupPlugin,
                  octoprint.plugin.SimpleApiPlugin,
                  octoprint.plugin.SettingsPlugin,
                  octoprint.plugin.TemplatePlugin):
	def __init__(self):
		self.logger = logging.getLogger("octoprint.plugins." + __name__)

		self.host = None
		self.port = None
		self.growl = None

		self.zeroconf_browse = None

	#~~ StartupPlugin API

	def on_startup(self, host, port):
		self.host = host
		self.port = port

	def on_after_startup(self):
		host = s.get(["hostname"])
		port = s.getInt(["port"])
		password = s.get(["password"])

		if not host:
			host = "localhost"
		if not port:
			port = 23053

		kwargs = dict(
			applicationName="OctoPrint",
			notifications=["File uploaded", "Print job started", "Print job done"],
			defaultNotifications=["Print job started", "Print job done"],
			hostname=host,
			port=port,
			password=password
		)
		import octoprint.util
		public_address = octoprint.util.address_for_client(host, port)
		if public_address:
			kwargs["applicationIcon"] = "http://{host}:{port}/static/img/tentacle-32x32.png".format(host=public_address, port=self.port)

		try:
			import gntp.notifier
			self.growl = gntp.notifier.GrowlNotifier(**kwargs)
			self.growl.register()

			helpers = octoprint.plugin.plugin_manager().get_helpers("discovery", helpers=["zeroconf_browse"])
			if helpers and "zeroconf_browse" in helpers:
				self.zeroconf_browse = helpers["zeroconf_browse"]
		except:
			self.logger.exception("Could not register with Growl at {host}:{port}, disabling...".format(host=host, port=port))
			self.growl = None

	#~~ TemplatePlugin API

	def get_template_vars(self):
		return dict(
			_settings_menu_entry="Growl"
		)

	def get_template_folder(self):
		import os
		return os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")

	#~~ SimpleApiPlugin API

	def get_api_commands(self):
		return None

	def on_api_command(self, command, data):
		return None

	def on_api_get(self, request):
		if not self.zeroconf_browse:
			return flask.jsonify(dict(
				browsing_enabled=False
			))

		browse_results = self.zeroconf_browse("_gntp._tcp", block=True)
		growl_instances = [dict(name=v["name"], host=v["host"], port=v["port"]) for v in browse_results]

		return flask.jsonify(dict(
			browsing_enabled=True,
			growl_instances=growl_instances
		))

	#~~ EventPlugin API

	def on_event(self, event, payload):
		if not self.growl:
			return

		import os

		noteType = title = description = None

		if event == octoprint.events.Events.UPLOAD:
			file = payload["file"]
			target = payload["target"]

			noteType = "File uploaded"
			title = "A new file was uploaded"
			description = "{file} was uploaded {targetString}".format(file=file, targetString="to SD" if target == "sd" else "locally")

		elif event == octoprint.events.Events.PRINT_STARTED:
			file = os.path.basename(payload["file"])
			origin = payload["origin"]

			noteType = "Print job started"
			title = "A new print job was started"
			description = "{file} has started printing {originString}".format(file=file, originString="from SD" if origin == "sd" else "locally")

		elif event == octoprint.events.Events.PRINT_DONE:
			file = os.path.basename(payload["file"])
			elapsed_time = payload["time"]

			noteType = "Print job done"
			title = "Print job finished"
			description = "{file} finished printing, took {elapsed_time} seconds".format(file=file, elapsed_time=elapsed_time)

		if noteType is None:
			return

		self.growl.notify(
			noteType = noteType,
			title = title,
			description = description,
			sticky = False,
			priority = 1
		)


__plugin_name__ = "Growl"
__plugin_description__ = "Get Growl notifications from OctoPrint"

__plugin_implementations__ = [GrowlPlugin()]