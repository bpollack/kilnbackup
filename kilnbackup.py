#! /usr/bin/env python

import ConfigParser, sys, urllib, urllib2, cookielib, os, subprocess, shutil

config = ConfigParser.ConfigParser()
config.read("kilnbackup.cfg")

save = False

if not config.has_section('kiln'):
	config.add_section('kiln')

settings = dict(config.items('kiln'))

def prompt(msg):
	print(prompt)
	value = sys.stdin.readline().strip()
	if not value:
		sys.exit()
	return value

def check(section, option, msg):
	if settings.get(option):
		return
	value = prompt(msg)
	global save
	save = True
	config.set(section, option, value)
	settings[option] = value

check("kiln", "server", "Enter the name of the fogbugz server (eg https://company.fogbugz.com)")
check("kiln", "username", "Username:")
check("kiln", "password", "Password:")

if save:
	f = open("kilnbackup.cfg", "w")
	config.write(f)
	f.flush()
	f.close()

server = settings["server"]

def get_repos():
	cj = cookielib.CookieJar()
	handler = urllib2.HTTPCookieProcessor(cj)
	opener = urllib2.build_opener(handler)

	data = urllib.urlencode({
		"pre":"preLogon", "fRememberPassword":"1", "dest":"",
		"sPerson":settings["username"], "sPassword":settings["password"]})
	response = opener.open(server + "/default.asp", data)
	response.read()
	response.close()
	
	response = opener.open(server + "/kiln/Api/Repos/")
	js = response.read()
	response.close()

	return js

def jseval(js):
	return eval(js, {"null":None, "true":True, "false":False})

def build_url(path):
	url = server + path
	return url.replace("://", "://%s:%s@" % (
			urllib.quote(settings["username"], ''),
			urllib.quote(settings["password"], '')
		))

for repo in jseval(get_repos()):
	url = build_url(repo["url"])
	name = os.path.split(repo["url"])[-1]

	if (os.path.exists(name)):
		hgrc = ConfigParser.ConfigParser()
		hgrc.read("%s/.hg/hgrc" % name)

		if not hgrc.has_section('paths') or hgrc.get('paths', 'default') != url:
			print "Deleting old repo", name
			shutil.rmtree(name)
	
	if os.path.exists(name):
		os.chdir(name)
		print "Pulling latest changes to", name
		subprocess.call(['hg', 'pull'])
		os.chdir("..")
	else:
		print "Cloninng", name
		subprocess.call(['hg', 'clone', '-U', url, name])


