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
from gtk import glade

from twisted.internet import protocol
from twisted.internet import reactor, defer
from twisted.python.util import println, sibpath
from twisted.web.client import getPage

import simplejson

class JolicloudRestoreUtilityBase(protocol.ProcessProtocol):
    _current_task = 0

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
        pass

    def errReceived(self, data):
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
    _hbox = None

    def __init__(self):
        self.start()

    def tasks_completed(self):
        print 'Completed! You need to restart your computer.'
        reactor.stop()

    def run_next_task(self):
        if self._current_task < len(self._tasks):
            print 'Executing task %d out of %d: %s' % (
                self._current_task + 1,
                len(self._tasks),
                self._tasks[self._current_task]['description']
            )
        JolicloudRestoreUtilityBase.run_next_task(self)

class JolicloudRestoreUtilityGtk(JolicloudRestoreUtilityBase, gtk.glade.XML):
    def __init__(self):
        self.glade = glade.XML(sibpath(__file__,"restore_utility.glade"))
        self.glade.signal_autoconnect(self)

        widgets = ("Dialog", "DialogVBox", "DialogActionArea", "CancelButton", "OKButton",
                "VBox", "Label", "Alignment", "ProgressBar")
        for widgetName in widgets:
            setattr(self, "_" + widgetName, self.glade.get_widget(widgetName))

    def on_Dialog_close(self, widget, userData=None):
        println(repr(userData))
        self.exit()

    def on_Dialog_response(self, widget, response):
        handlers = {
            gtk.RESPONSE_NONE: self.exit,
            gtk.RESPONSE_DELETE_EVENT: self.exit,
            gtk.RESPONSE_OK: self.doRestore,
            gtk.RESPONSE_CANCEL: self.cancelled
        }
        handlers.get(response)()

    def exit(self):
        reactor.stop()

    def cancelled(self):
        self._Dialog.destroy()
        self.exit()

    def doRestore(self):
        self.start()

    def run_next_task(self):
        if self._current_task < len(self._tasks):
            self._ProgressBar.set_text(self._tasks[self._current_task]['description'])
            self._ProgressBar.set_fraction((self._current_task+1)/float(len(self._tasks)))
        JolicloudRestoreUtilityBase.run_next_task(self)

    def tasks_completed(self):
        self.exit()

def do_restore():
    if os.environ.get('DISPLAY', False):
        JolicloudRestoreUtilityGtk()
    else:
        JolicloudRestoreUtilityText()
    reactor.run()

if __name__ == '__main__':
    do_restore()
