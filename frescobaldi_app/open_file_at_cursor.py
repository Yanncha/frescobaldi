# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2014 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
Opens a file the current textcursor points at (or has selected).

Generate the include files' tooltips
"""


import os

from PyQt5.QtCore import QUrl 

import documentinfo
import browseriface

def includeTarget(cursor):
    """Given a cursor determine an absolute path to an include file present in the cursor's block.
    Return path or empty string if no valid file is found.

    Note that currently this still operates on the full block, i.e. considers the first \include
    within the block. It should be narrowed down to an actual string below the mouse pointer.
    """

    # determine current block's range
    block = cursor.block()
    start = block.position()
    end = start + len(block.text()) + 1

    # TODO:
    # I think this should be approached differently.
    # There is no need to have documentinfo process the whole document.
    # All we want is to parse the text around the cursor, which should be implemented locally.
    # (This will also make it easier to narrow the selection down to the actual mouse pointer position)
    dinfo = documentinfo.info(cursor.document())
    i = dinfo.lydocinfo().range(start, end)
    fnames = i.include_args() or i.scheme_load_args()
    if not fnames:
        return ""

    # determine search path: doc dir and other include path names
    filename = cursor.document().url().toLocalFile()
    path = [os.path.dirname(filename)] if filename else []
    path.extend(dinfo.includepath())

    targets = []
    # iterating over the search paths, find the first combination pointing to an existing file
    for f in fnames:
        for p in path:
            name = os.path.normpath(os.path.join(p, f))
            if os.path.exists(name) and not os.path.isdir(name):
                targets.append(name)
                continue
    return targets

def genToolTipInfo(cursor):
    """Return a list of infomation of the inlude files.
    
    For each include file,  generate a ToolTipInfo instance. Insert it into the list. 
    
    A ToolTipInfo instance has two attribute:
    
    - content: the content of the tooltip for this include file
    
    - num:     number of the block where this include file locates 

    """    
    dinfo = documentinfo.info(cursor.document()) 
    
    # get the path of current file
    filename = cursor.document().url().toLocalFile()
    path = [os.path.dirname(filename)] if filename else []
    path.extend(dinfo.includepath())
    
    toolTipInfo = []
    
    # startIndex is the content where every find begins
    startIndex = 0
    
    # find the first '\include'
    pointCursor = cursor.document().find('\include', startIndex)
    
    # find an include file each loop
    while not pointCursor.isNull():
        block = pointCursor.block()
        text = block.text()
        head = block.position()
        tail = head + block.length()
        i = dinfo.lydocinfo().range(head, tail)
        fnames = i.include_args() or i.scheme_load_args()
        
        # update startIndex
        startIndex = tail
        if not fnames:
            continue
        
        # file information unit
        info = {}
        info['num'] = block.blockNumber()
        
        # whether we can find a valid file path
        valid = False
        for f in fnames:
            for p in path:
                name = os.path.normpath(os.path.join(p, f))
                if os.path.exists(name) and not os.path.isdir(name):
                    info['content'] = name
                    valid = True
                    break
        if valid == False:
            info['content'] = "This is an invalid include file"
        toolTipInfo.append(info)
        
        # find next '\inluded'
        pointCursor = cursor.document().find('\include', startIndex)
    return toolTipInfo        
    
def filenames_at_cursor(cursor, existing=True):
    """Return a list of filenames at the cursor.

    If existing is False, also names are returned that do not exist on disk.

    """
    # take either the selection or the include-args found by lydocinfo
    start = cursor.document().findBlock(cursor.selectionStart()).position()
    end = cursor.selectionEnd()
    if not cursor.hasSelection():
        end = start + len(cursor.block().text()) + 1
    dinfo = documentinfo.info(cursor.document())
    i = dinfo.lydocinfo().range(start, end)
    fnames = i.include_args() or i.scheme_load_args() 
    if not fnames and cursor.hasSelection():
        text = cursor.selection().toPlainText()
        if '\n' not in text.strip():
            fnames = [text]

    # determine search path: doc dir and other include path names
    filename = cursor.document().url().toLocalFile()
    directory = os.path.dirname(filename)
    if filename:
        path = [directory]
    else:
        path = []
    path.extend(dinfo.includepath())

    # find all docs, trying all include paths
    filenames = []
    for f in fnames:
        for p in path:
            name = os.path.normpath(os.path.join(p, f))
            if os.access(name, os.R_OK):
                filenames.append(name)
                break
        else:
            if not existing:
                name = os.path.normpath(os.path.join(directory, f))
                filenames.append(name)
    return filenames

def open_file_at_cursor(mainwindow, cursor=None):
    """Open the filename(s) mentioned at the mainwindow's text cursor.

    Return True if there were one or more filenames that were opened.

    """
    if cursor is None:
        cursor = mainwindow.textCursor()
    return open_targets(filenames_at_cursor(cursor))

def open_targets(mainwindow, targets):
    """Open all given files, giving focus to the last one.

    Return True if there were one or more filenames that were opened.

    """
    d = None
    for t in targets:
        d = mainwindow.openUrl(QUrl.fromLocalFile(t))
    if d:
        browseriface.get(mainwindow).setCurrentDocument(d, True)
        return True
