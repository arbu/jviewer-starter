#! /usr/bin/env python
# coding: utf-8
#
# Copyright 2017 Aaron Bulmahn (aarbudev@gmail.com)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Intel Corporation nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

loginUrl="http://{0}/rpc/WEBSES/create.asp"
jnlpUrl = "http://{0}/Java/jviewer.jnlp?EXTRNIP={0}&JNLPSTR=JViewer"
jarBase = "http://{0}/Java/release/"
mainClass = "com.ami.kvm.jviewer.JViewer"

try:
    # Python 3
    from urllib.request import urlopen, urlretrieve, Request
    from urllib.parse import urlencode
    from http.client import IncompleteRead
except ImportError:
    # Python 2
    from urllib import urlencode, urlretrieve
    from urllib2 import urlopen, Request
    class IncompleteRead(object):
        pass
    input = raw_input

import sys, os, re, subprocess, platform, getpass, zipfile

def update_jars(server):
    base = jarBase.format(server)
    system = platform.system()
    if system == "Linux":
        natives = "Linux_x86_"
        path = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    elif system == "Windows":
        natives = "Win"
        path = os.environ.get("LOCALAPPDATA")
    elif system == "Darwin":
        natives = "Mac"
        path = os.path.expanduser('~/Library/Application Support')
    else:
        raise Exception("OS not supportet: " + system)
    natives += platform.architecture()[0][:2] + ".jar"
    path = os.path.join(path, "jviewer-starter")

    if not os.path.exists(path):
        os.makedirs(path)
    for jar in ["JViewer.jar", "JViewer-SOC.jar", natives]:
        jar_path = os.path.join(path, jar)
        if not os.path.exists(jar_path):
            print("downloading %s -> %s" % (base + jar, jar_path))
            try:
                urlretrieve(base + jar, jar_path)
            except Exception as e:
                if jar == "JViewer-SOC.jar":
                    print("Ignored SOC file")
                    continue
                else:
                    raise e
            if jar == natives:
                print("extracting %s" % jar_path)
                with zipfile.ZipFile(jar_path, 'r') as natives_jar:
                    natives_jar.extractall(path)

    return path

def run_jviewer(server, username, password, path):
    credentials = {"WEBVAR_USERNAME": username, "WEBVAR_PASSWORD": password}

    loginRequest = Request(loginUrl.format(server))
    loginRequest.data = urlencode(credentials).encode("utf-8")
    loginResponse = urlopen(loginRequest).read().decode("utf-8")
    sessionCookie = re.search("'SESSION_COOKIE' : '([a-zA-Z0-9]+)'", loginResponse).group(1)

    jnlpRequest = Request(jnlpUrl.format(server))
    jnlpRequest.add_header("Cookie", "SessionCookie=%s" % sessionCookie)
    try:
        jnlpResponse = urlopen(jnlpRequest).read().decode("utf-8")
    except IncompleteRead as e:
        # The server sends a wrong Content-length header. We just ignore it
        jnlpResponse = e.partial.decode("utf-8")

    args = ["java"]
    args.append("-Djava.library.path=" + path)
    args.append("-cp")
    args.append(os.path.join(path, "*"))
    args.append(mainClass)
    args += re.findall("<argument>([^<]+)</argument>", jnlpResponse)

    print(" ".join(args))
    subprocess.call(args)

if __name__ == "__main__":
    server = sys.argv[1] if len(sys.argv) > 1 else input("Server: ")
    path = update_jars(server)
    username = sys.argv[2] if len(sys.argv) > 2 else input("Username: ")
    password = sys.argv[3] if len(sys.argv) > 3 else getpass.getpass()
    run_jviewer(server, username, password, path)
