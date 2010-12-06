#!/usr/bin/env python
# -*- coding: utf-8 -*-

import warnings

warnings.simplefilter("ignore")
from twisted.internet import gtk2reactor
gtk2reactor.install()
warnings.simplefilter("default")

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
from twisted.python.lockfile import FilesystemLock
from twisted.web.client import getPage

import simplejson

class JolicloudRestoreUtilityBase(protocol.ProcessProtocol):
    _current_task = 0

    _default_tasks = [
            {
                "task": "clear_packages",
                "description": "Clearing out the local repository of package files.",
                "details": "Clear out the local repository of package files."
            },
            {
                "task": "clear_nickel_cache",
                "description": "Clearing browser cache.",
                "details": "Clear browser cache."
            },
            {
                "task": "configure_pending_packages",
                "description": "Configuring pending packages.",
                "details": "Configure pending packages."
            },
            {
                "task": "update",
                "description": "Updating package index files.",
                "details": "Update package index files."
            },
            {
                "task": "install",
                "args": {"packages": ["jolicloud-desktop"]},
                "description": "Forcing default packages installation.",
                "details": "Force default packages installation."
            },
            {
                "task": "upgrade",
                "description": "Upgrading system.",
                "details": "Upgrade system."
            },
            {
                "task": "clear_packages",
                "description": "Clearing out the local repository of package files.",
                "details": "Clear out the local repository of package files."
            }
        ]

    def update_tasks_list(self, tasks):
        self._tasks = tasks

    def tasks_download_errback(self, error):
        self.update_tasks_list(self._default_tasks)

    def tasks_download_callback(self, result):
        tasks = simplejson.loads(result)
        if not isinstance(tasks, list):
            tasks = self._default_tasks
        self.update_tasks_list(tasks)

    """ Tasks """
    def _task_clear_packages(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', '-y', 'clean'], env=None
        )

    def _task_clear_nickel_cache(self):
        reactor.spawnProcess(
            self,
            '/bin/rm',
            ['rm', '-fr'] + glob.glob('/home/*/.config/google-chrome/Default/Application Cache/*'), {}
        )

    def _task_configure_pending_packages(self):
        """
        dpkg --configure --pending
        """
        reactor.spawnProcess(
            self,
            '/usr/bin/dpkg',
            ['dpkg', '--configure', '--pending'], env=None
        )

    def _task_update(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', '-y', 'update'], env=None
        )

    def _task_install(self, packages=[]):
        if packages:
            reactor.spawnProcess(
                self,
                '/usr/bin/apt-get',
                ['apt-get', '-y', '-f', 'install'] + map(str, packages), env=None
            )

    def _task_reinstall(self, packages=[]):
        if packages:
            reactor.spawnProcess(
                self,
                '/usr/bin/apt-get',
                ['apt-get', '-y', '-f', '--purge', '--reinstall', 'install'] + map(str, packages), env=None
            )

    def _task_upgrade(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', '-y', 'dist-upgrade'], env=None
        )
    """ End Tasks """

    def __init__(self):
        getPage("http://my.jolicloud.com/restore.json", timeout=10).addCallback(self.tasks_download_callback).addErrback(self.tasks_download_errback)

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
    def update_tasks_list(self, tasks):
        JolicloudRestoreUtilityBase.update_tasks_list(self, tasks)
        self.run_next_task()

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

class JolicloudRestoreUtilityGtk(JolicloudRestoreUtilityBase):
    running = False
    complete = False

    def __init__(self):
        self.glade = glade.XML(sibpath(__file__,"restore_utility.glade"))
        self.glade.signal_autoconnect(self)

        for widget in self.glade.get_widget_prefix(""):
            setattr(self, "_" + widget.get_name(), widget)

        self._ProgressBar.unmap()
        self._OKButton.set_sensitive(False) # wait for tasks list to get updated

        JolicloudRestoreUtilityBase.__init__(self)

    def update_tasks_list(self,tasks):
        JolicloudRestoreUtilityBase.update_tasks_list(self, tasks)
        text = ""
        for d in [t['details'] for t in tasks]:
            text += d+"\n"
        self._Details.get_buffer().set_text(text.strip())
        self._OKButton.set_sensitive(True)

    def on_Dialog_close(self, widget, userData=None):
        self.exit()

    def on_Dialog_response(self, widget, response):
        handlers = {
            gtk.RESPONSE_NONE: self.exit,
            gtk.RESPONSE_DELETE_EVENT: self.exit,
            gtk.RESPONSE_OK: self.doRestore,
            gtk.RESPONSE_CANCEL: self.cancelled
        }
        if self.complete:
            handlers[gtk.RESPONSE_OK] = self.exit
        handlers.get(response)()

    def exit(self):
        if self.running:
            if self._Dialog:
                self._Dialog.hide()
            return True
        if self._Dialog:
            self._Dialog.destroy()
        reactor.stop()

    def cancelled(self):
        self.exit()

    def doRestore(self):
        self.running = True
        self._ProgressBar.map()
        self._OKButton.set_sensitive(False)
        self._CancelButton.set_sensitive(False)
        self._Details.get_buffer().set_text("")
        self._Dialog.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        reactor.callLater(0, self.run_next_task)

    def run_next_task(self):
        if self._current_task < len(self._tasks):
            self._ProgressBar.set_text(self._tasks[self._current_task]['description'])
            self._ProgressBar.set_fraction((self._current_task+1)/float(len(self._tasks)))
        JolicloudRestoreUtilityBase.run_next_task(self)

    def tasks_completed(self):
        self.running = False
        self.complete = True
        self._Dialog.present()
        self._OKButton.set_sensitive(True)
        self._ProgressBar.set_text("All operations complete!")
        self._ProgressBar.set_fraction(1.0)

    def outReceived(self, data):
        if hasattr(self, "_Details"):
            buf = self._Details.get_buffer()
            i = buf.get_end_iter()
            buf.insert(i,data)
            self._Details.scroll_mark_onscreen(buf.get_insert())

    def errReceived(self, data):
        if hasattr(self, "_Details"):
            buf = self._Details.get_buffer()
            i = buf.get_end_iter()
            buf.insert(i,data)
            self._Details.scroll_mark_onscreen(buf.get_insert())

def do_restore():
    lock = FilesystemLock("/var/run/jolicloud_restore_utility.lock")
    if lock.lock():
        if os.environ.get('DISPLAY', False):
            JolicloudRestoreUtilityGtk()
        else:
            JolicloudRestoreUtilityText()
        reactor.run()
        lock.unlock()

if __name__ == '__main__':
    do_restore()
