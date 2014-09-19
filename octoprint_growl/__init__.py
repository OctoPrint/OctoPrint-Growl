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
	"hostname": "localhost",
	"port": 23053,
	"password": None,
}
s = octoprint.plugin.plugin_settings("growl", defaults=default_settings)

class GrowlMessages(object):
	TEST = "Connection test"
	FILE_UPLOADED = "File uploaded"
	PRINT_STARTED = "Printjob started"
	PRINT_DONE = "Printjob done"
	TIMELAPSE_DONE = "Timelapse done"

class GrowlPlugin(octoprint.plugin.EventHandlerPlugin,
                  octoprint.plugin.StartupPlugin,
                  octoprint.plugin.SimpleApiPlugin,
                  octoprint.plugin.SettingsPlugin,
                  octoprint.plugin.TemplatePlugin,
                  octoprint.plugin.AssetPlugin):
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

		helpers = octoprint.plugin.plugin_manager().get_helpers("discovery", "zeroconf_browse")
		if helpers and "zeroconf_browse" in helpers:
			self.zeroconf_browse = helpers["zeroconf_browse"]

		self.growl, _ = self._register_growl(host, port, password=password)


	#~~ TemplatePlugin API

	def get_template_vars(self):
		return dict(
			_settings_menu_entry="Growl"
		)

	def get_template_folder(self):
		import os
		return os.path.join(os.path.dirname(os.path.realpath(__file__)), "templates")

	##~~ AssetPlugin API

	def get_asset_folder(self):
		import os
		return os.path.join(os.path.dirname(os.path.realpath(__file__)), "static")

	def get_assets(self):
		return {
			"js": ["js/growl.js"],
			"css": ["css/growl.css"],
			"less": ["less/growl.less"]
		}

	#~~ SimpleApiPlugin API

	def get_api_commands(self):
		return dict(
			test=["host", "port"]
		)

	def on_api_command(self, command, data):
		if command == "test":
			import gntp.notifier
			growl, message = self._register_growl(data["host"], data["port"], password=data["password"])
			if growl:
				try:
					growl.notify(
						noteType=GrowlMessages.TEST,
						title = "This is a test message",
						description = "If you can read this, OctoPrint successfully registered with this Growl instance"
					)
					return flask.jsonify(dict(success=True))
				except Exception as e:
					self.logger.exception("Sending test message to Growl instance on {host}:{port} failed".format(host=data["host"], port=data["port"]))
					return flask.jsonify(dict(success=False, msg=str(e.message)))
			else:
				return flask.jsonify(dict(success=False, msg=str(message)))

		return flask.make_response("Unknown command", 400)

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

	##~~ SettingsPlugin API

	def on_settings_load(self):
		return dict(
			hostname=s.get(["hostname"]),
			port=s.getInt(["port"]),
			password=s.get(["password"])
		)

	def on_settings_save(self, data):
		if "hostname" in data and data["hostname"]:
			s.set(["hostname"], data["hostname"])
		if "port" in data and data["port"]:
			s.setInt(["port"], data["port"])
		if "password" in data:
			s.set(["password"], data["password"])

		def register(host, port, password):
			self.growl = self._register_growl(host, port, password=password)

		import threading
		thread = threading.Thread(target=register, args=(s.get(["hostname"]), s.getInt(["port"]), s.get(["password"])))
		thread.daemon = False
		thread.start()

	#~~ EventPlugin API

	def on_event(self, event, payload):
		growl = self.growl
		if not growl:
			return

		import os

		noteType = title = description = None

		if event == octoprint.events.Events.UPLOAD:
			file = payload["file"]
			target = payload["target"]

			noteType = GrowlMessages.FILE_UPLOADED
			title = "A new file was uploaded"
			description = "{file} was uploaded {targetString}".format(file=file, targetString="to SD" if target == "sd" else "locally")

		elif event == octoprint.events.Events.PRINT_STARTED:
			file = os.path.basename(payload["file"])
			origin = payload["origin"]

			noteType = GrowlMessages.PRINT_STARTED
			title = "A new print job was started"
			description = "{file} has started printing {originString}".format(file=file, originString="from SD" if origin == "sd" else "locally")

		elif event == octoprint.events.Events.PRINT_DONE:
			file = os.path.basename(payload["file"])
			elapsed_time = payload["time"]

			noteType = GrowlMessages.PRINT_DONE
			title = "Print job finished"
			description = "{file} finished printing, took {elapsed_time} seconds".format(file=file, elapsed_time=elapsed_time)

		if noteType is None:
			return

		growl.notify(
			noteType = noteType,
			title = title,
			description = description,
			sticky = False,
			priority = 1
		)

	##~~ Helpers

	def _register_growl(self, host, port, password):
		kwargs = dict(
			applicationName="OctoPrint",
			notifications=[getattr(GrowlMessages, msg) for msg in dir(GrowlMessages) if not msg.startswith("_")],
			defaultNotifications=[GrowlMessages.TEST, GrowlMessages.PRINT_STARTED, GrowlMessages.PRINT_DONE],
			hostname=host,
			port=port,
			password=password
		)
		import octoprint.util
		public_address = octoprint.util.address_for_client(host, port)
		if public_address:
			kwargs["applicationIcon"] = "http://{host}:{port}/static/img/tentacle-32x32.png".format(host=public_address, port=self.port)

		self.logger.debug("Sending applicationIcon = {applicationIcon}".format(**kwargs))

		try:
			import gntp.notifier
			growl = gntp.notifier.GrowlNotifier(**kwargs)
			growl.socketTimeout = 5
			growl.register()
			return growl, None
		except Exception as e:
			self.logger.warn("Could not register with Growl at {host}:{port}: {msg}".format(host=host, port=port, msg=e.message))
			return None, e.message



__plugin_name__ = "Growl"
__plugin_description__ = "Get Growl notifications from OctoPrint"
__plugin_implementations__ = [GrowlPlugin()]
