# coding=utf-8
import setuptools

def package_data_dirs(source, sub_folders):
	import os
	dirs = []

	for d in sub_folders:
		for dirname, _, files in os.walk(os.path.join(source, d)):
			dirname = os.path.relpath(dirname, source)
			for f in files:
				dirs.append(os.path.join(dirname, f))

	return dirs

def params():
	name = "OctoPrint-Growl"
	version = "0.1.0"

	description = "Adds support for Growl/GNTP to OctoPrint"
	long_description = "TODO"
	author = "Gina Häußge"
	author_email = "osd@foosel.net"
	url = "http://octoprint.org"
	license = "AGPLv3"

	packages = ["octoprint_growl"]
	package_data = {"octoprint": package_data_dirs('octoprint_growl', ['static', 'templates'])}

	include_package_data = True
	zip_safe = False
	install_requires = open("requirements.txt").read().split("\n")

	entry_points = {
		"octoprint.plugin": [
			"growl = octoprint_growl"
		]
	}

	return locals()

setuptools.setup(**params())
