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
                "task": "autoremove",
                "description": "Auto-removing unnecessary packages.",
                "details": "Auto-remove packages no longer required on the system, like unused dependencies."
            },
            {
                "task": "clear_packages",
                "description": "Clearing out the local repository of package files.",
                "details": "Clear out the local repository of package files."
            },
            {
                "task": "cleanup_topbar",
                "description": "Cleaning up the topbar and resetting applets location.",
                "details": "Clean up the topbar and reset applets location."
            },
            {
                "task": "reload_gnome_panel",
                "description": "Reloading the GNOME panel.",
                "details": "Reload the GNOME panel."
            },
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
            '/bin/sh',
            [
            'sh', '-c',
            '/bin/rm -rf /home/' + os.environ['SUDO_USER'] + '/.config/google-chrome/Default/Application\ Cache/ ' +
                '&& pkill nickel-browser && pkill nickel-browser'
            ], {}
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

    def _task_autoremove(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/apt-get',
            ['apt-get', '-y', '--purge', 'autoremove'], env=None
        )

    def _task_cleanup_topbar(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/sudo',
            ['sudo', '-E', '-u', os.environ['SUDO_USER'], 'gconftool-2', '--recursive-unset', '/apps/panel'], env=None
        )

    def _task_reload_gnome_panel(self):
        reactor.spawnProcess(
            self,
            '/usr/bin/killall',
            ['killall', 'gnome-panel'], env=None
        )

    """ End Tasks """

    def __init__(self):
        getPage("http://my.jolicloud.com/restore.json", agent="JRU 0.5", timeout=10).addCallback(self.tasks_download_callback).addErrback(self.tasks_download_errback)

    def run_next_task(self):
        if self._current_task < len(self._tasks):
            current_task = self._tasks[self._current_task]
            if not current_task['disabled'] and hasattr(self, '_task_%s' % current_task['task']):
                kwargs = {}
                if self._tasks[self._current_task].has_key('args'):
                    for key, val in self._tasks[self._current_task]['args'].iteritems():
                        kwargs[str(key)] = val
                getattr(self, '_task_%s' % self._tasks[self._current_task]['task'])(**kwargs)
                self._current_task += 1
            # ignore disabled/unknown tasks
            else:
                self._current_task += 1
                self.run_next_task()
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

        #for widget in self.glade.get_widget_prefix(""):
        #    setattr(self, "_" + widget.get_name(), widget)

        self.glade.get_widget('ProgressBar').unmap()
        self.glade.get_widget('Details').hide()
        self.glade.get_widget('OKButton').set_sensitive(False) # wait for tasks list to get updated

        JolicloudRestoreUtilityBase.__init__(self)

    def update_tasks_list(self, tasks):
        vb = self.glade.get_widget('VBox2')
        JolicloudRestoreUtilityBase.update_tasks_list(self, tasks)
        for t in tasks:
            adj = self.glade.get_widget('ScrolledWindow').get_vadjustment()
            cb = gtk.CheckButton(t['details'], False)
            t['widget'] = cb
            cb.connect('toggled',self.toggle_task,t)
            cb.connect('focus_in_event', self.focus_in, adj)
            cb.set_active(True)
            vb.pack_start(cb)
            cb.show()
        self.glade.get_widget('OKButton').set_sensitive(True)

    def toggle_task(self, widget, task):
        if widget.get_active():
            task['disabled'] = False
        else:
            task['disabled'] = True

    def focus_in(self, widget, event, adj):
        alloc = widget.get_allocation()
        if alloc.y < adj.value or alloc.y > adj.value + adj.page_size:
            adj.set_value(min(alloc.y, adj.upper-adj.page_size))

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
            #if hasattr(self,"_Dialog"):
            self.glade.get_widget('Dialog').hide()
            return True
        #if hasattr(self,"_Dialog"):
        self.glade.get_widget('Dialog').destroy()
        reactor.stop()

    def cancelled(self):
        self.exit()

    def doRestore(self):
        self.running = True
        self.glade.get_widget('ProgressBar').map()
        self.glade.get_widget('OKButton').set_sensitive(False)
        self.glade.get_widget('CancelButton').set_sensitive(False)
        self.glade.get_widget('Details').get_buffer().set_text("")
        self.glade.get_widget('Dialog').window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        for t in self._tasks:
            t['widget'].hide()
        self.glade.get_widget('Details').show()
        reactor.callLater(0, self.run_next_task)

    def run_next_task(self):
        if self._current_task < len(self._tasks):
            self.glade.get_widget('ProgressBar').set_fraction((self._current_task+1)/float(len(self._tasks)))
            current_task = self._tasks[self._current_task]
            if not current_task['disabled']:
                self.glade.get_widget('ProgressBar').set_text(current_task['description'])
                buf = self.glade.get_widget('Details').get_buffer()
                i = buf.get_end_iter()
                buf.insert(i,current_task['description']+'\n')
                self.glade.get_widget('Details').scroll_mark_onscreen(buf.get_insert())
        JolicloudRestoreUtilityBase.run_next_task(self)

    def tasks_completed(self):
        self.running = False
        self.complete = True
        self.glade.get_widget('Dialog').present()
        self.glade.get_widget('OKButton').set_sensitive(True)
        self.glade.get_widget('ProgressBar').set_text("All operations complete!")
        self.glade.get_widget('ProgressBar').set_fraction(1.0)
        self.glade.get_widget('Dialog').window.set_cursor(None)
        buf = self.glade.get_widget('Details').get_buffer()
        i = buf.get_end_iter()
        buf.insert(i,'Done.')
        self.glade.get_widget('Details').scroll_mark_onscreen(buf.get_insert())

    def outReceived(self, data):
        #if hasattr(self, "_Details"):
        buf = self.glade.get_widget('Details').get_buffer()
        i = buf.get_end_iter()
        buf.insert(i,data)
        self.glade.get_widget('Details').scroll_mark_onscreen(buf.get_insert())

    def errReceived(self, data):
        #if hasattr(self, "_Details"):
        buf = self.glade.get_widget('Details').get_buffer()
        i = buf.get_end_iter()
        buf.insert(i,data)
        self.glade.get_widget('Details').scroll_mark_onscreen(buf.get_insert())

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
