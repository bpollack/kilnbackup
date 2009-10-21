#! /usr/bin/env python

# Copyright (c) 2009 Stefan Rusek
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import ConfigParser, sys, urllib, urllib2, cookielib, os, subprocess, shutil, time

config = ConfigParser.RawConfigParser()
config.read("kilnbackup.cfg")

save = False

if not config.has_section('kiln'):
	config.add_section('kiln')

settings = dict(config.items('kiln'))

def prompt(msg):
	print(msg)
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
		hgrc = ConfigParser.SafeConfigParser()
		hgrc.read("%s/.hg/hgrc" % name)

		if not hgrc.has_section('paths') or hgrc.get('paths', 'default') != url:
			print "Deleting old repo", name
			if not os.path.exists("archive"): os.mkdir("archive")
			shutil.move(name, "archive/%f-%s" % (time.time(), name))
	
	if os.path.exists(name):
		os.chdir(name)
		print "Pulling latest changes to", name
		subprocess.call(['hg', 'pull'])
		os.chdir("..")
	else:
		print "Cloninng", name
		subprocess.call(['hg', 'clone', '-U', url, name])


