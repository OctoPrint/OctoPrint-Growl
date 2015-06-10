# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2014 The OctoPrint Project - Released under terms of the AGPLv3 License"

import flask

import octoprint.plugin
import octoprint.events

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
		self.host = None
		self.port = None
		self.growl = None

		self.zeroconf_browse = None

	#~~ StartupPlugin API

	def on_startup(self, host, port):
		self.host = host
		self.port = port

	def on_after_startup(self):
		host = self._settings.get(["hostname"])
		port = self._settings.get_int(["port"])
		password = self._settings.get(["password"])

		helpers = self._plugin_manager.get_helpers("discovery", "zeroconf_browse")
		if helpers and "zeroconf_browse" in helpers:
			self.zeroconf_browse = helpers["zeroconf_browse"]

		self.growl, _ = self._register_growl(host, port, password=password)

	##~~ SettingsPlugin API

	def get_settings_defaults(self):
		return {
			"hostname": "localhost",
			"port": 23053,
			"password": None,
		    "timeout": 10
		}

	##~~ AssetPlugin API

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
					self._logger.exception("Sending test message to Growl instance on {host}:{port} failed".format(host=data["host"], port=data["port"]))
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

	def on_settings_save(self, data):
		super(GrowlPlugin, self).on_settings_save(data)

		def register(host, port, password):
			self.growl = self._register_growl(host, port, password=password)

		import threading
		thread = threading.Thread(target=register, args=(self._settings.get(["hostname"]), self._settings.get_int(["port"]), self._settings.get(["password"])))
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

	##~~ Softwareupdate hook

	def get_update_information(self):
		return dict(
			growl=dict(
				displayName="Growl Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="OctoPrint",
				repo="OctoPrint-Growl",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/OctoPrint/OctoPrint-Growl/archive/{target_version}.zip"
			)
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

		self._logger.debug("Sending applicationIcon = {applicationIcon}".format(**kwargs))

		try:
			import gntp.notifier
			growl = gntp.notifier.GrowlNotifier(**kwargs)
			growl.socketTimeout = self._settings.get_int(["timeout"])
			growl.register()
			return growl, None
		except Exception as e:
			self._logger.warn("Could not register with Growl at {host}:{port}: {msg}".format(host=host, port=port, msg=e.message))
			return None, e.message



__plugin_name__ = "Growl"
def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = GrowlPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
