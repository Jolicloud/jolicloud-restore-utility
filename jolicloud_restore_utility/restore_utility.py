#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.internet import gtk2reactor
gtk2reactor.install()

import os
import sys
import glob
import traceback
import datetime
import pygtk
pygtk.require('2.0')
import gtk

from twisted.internet import protocol
from twisted.internet import reactor, defer
from twisted.python.util import println
from twisted.web.client import getPage

import simplejson

class JolicloudRestoreUtilityBase(protocol.ProcessProtocol):
    _current_task = 0

    _tasks = None
    _default_tasks = [
            {
                'task': 'clear_packages',
                'description': 'Clearing packages.'
            },
            {
                'task': 'clear_nickel_cache',
                'description': 'Clearing Nickel Browser cache.'
            },
            {
                'task': 'reconfigure_packages',
                'description': 'Reconfiguring packages.'
            },
            {
                'task': 'update',
                'description': 'Updating packages base.'
            },
            {
                'task': 'install',
                'args': {'packages': ['jolicloud-desktop']},
                'description': 'Forcing default packages installation.'
            },
            {
                'task': 'upgrade',
                'description': 'Upgrading system.'
            },
            {
                'task': 'clear_packages',
                'description': 'Clearing packages.'
            }
        ]

    def tasks_download_errback(self, error):
        self._tasks = self._default_tasks
        self.run_next_task()

    def tasks_download_callback(self, result):
        self._tasks = simplejson.loads(result)
        if not isinstance(self._tasks, list):
            self._tasks = self._default_tasks
        self.run_next_task()

    """ Tasks """
    def _task_clear_packages(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', 'clean'], {'DEBIAN_FRONTEND': 'noninteractive'}
        )

    def _task_clear_nickel_cache(self):
        reactor.spawnProcess(
            self,
            '/bin/rm',
            ['rm', '-fr'] + glob.glob('/home/*/.config/google-chrome/Default/Application Cache/*'), {}
        )

    def _task_reconfigure_packages(self):
        """
        dpkg-reconfigure --all --force
        """
        reactor.spawnProcess(
            self,
            '/usr/sbin/dpkg-reconfigure',
            ['dpkg-reconfigure', '--all', '--force'], {'DEBIAN_FRONTEND': 'noninteractive'}
        )

    def _task_update(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', 'update'], {'DEBIAN_FRONTEND': 'noninteractive'}
        )
    
    def _task_install(self, packages=[]):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', '-f', 'install'] + packages, {'DEBIAN_FRONTEND': 'noninteractive'}
        )
    
    def _task_reinstall(self, packages=[]):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', '-f', '--purge', '--reinstall', 'install'] + packages, {'DEBIAN_FRONTEND': 'noninteractive'}
        )

    def _task_upgrade(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', 'dist-upgrade'], {'DEBIAN_FRONTEND': 'noninteractive'}
        )
    """ End Tasks """

    def start(self):
        getPage("http://dev.jolicloud.org/~benjamin/tasks").addCallback(self.tasks_download_callback).addErrback(self.tasks_download_errback)

    def run_next_task(self):
        if self._current_task < len(self._tasks):
            print 'Executing task %d out of %d: %s' % (
                self._current_task + 1,
                len(self._tasks),
                self._tasks[self._current_task]['description']
            )
            if hasattr(self, '_task_%s' % self._tasks[self._current_task]['task']):
                kwargs = {}
                if self._tasks[self._current_task].has_key('args'):
                    for key, val in self._tasks[self._current_task]['args'].iteritems():
                        kwargs[str(key)] = val
                getattr(self, '_task_%s' % self._tasks[self._current_task]['task'])(**kwargs)
                self._current_task += 1
        else:
            self.tasks_completed()

    def connectionMade(self):
        pass
    
    def outReceived(self, data):
        #print "[%s][stdout] %s" % (datetime.datetime.now(), data)
        pass
    
    def errReceived(self, data):
        #print "[%s][stderr] %s" % (datetime.datetime.now(), data)
        pass
        
    def inConnectionLost(self):
        pass
    
    def outConnectionLost(self):
        pass
    
    def errConnectionLost(self):
        pass
    
    def processEnded(self, status_object):
        self.run_next_task()

class JolicloudRestoreUtilityText(JolicloudRestoreUtilityBase):
    def __init__(self):
        self.start()

    def tasks_completed(self):
        print 'Completed! You need to restart your computer.'
        reactor.stop()

class JolicloudRestoreUtilityGtk(JolicloudRestoreUtilityBase, gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        
        self.set_icon(self.render_icon(gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU))
        self.connect('map-event', self._on_map_event)
        self.connect('destroy', self._destroy_cb)
        self._build_welcome_message()
        self.show_all()
    
    def _destroy_cb(self, window):
        self.destroy()
        #gtk.main_quit()
        reactor.stop()

    def _on_map_event(self, event, m):
        pass

    def _restore(self, button):
        self.start()

    def _build_welcome_message(self):
        vbox = gtk.VBox()
        label = gtk.Label('Bla bla bla...')
        button = gtk.Button('Okay, I understand')
        button.connect('clicked', self._restore)
        vbox.pack_start(label)
        hbox = gtk.HBox()
        hbox.pack_start(button)
        vbox.pack_end(hbox)
        self.add(vbox)

def do_restore():
    if os.environ.get('DISPLAY', False):
        JolicloudRestoreUtilityGtk()
    else:
        JolicloudRestoreUtilityText()
    reactor.run()

if __name__ == '__main__':
    do_restore()

