from mutagen.mp3 import MP3
from mutagen.mp3 import HeaderNotFoundError
#from mutagen.mp3 import _util
from mutagen.mp3 import MPEGInfo
from mutagen.flac import FLAC
from mutagen.ogg import OggFileType
from mutagen.oggvorbis import OggVorbis
from mutagen.oggvorbis import OggVorbisInfo
from mutagen.aac import AAC
from mutagen.id3 import ID3, ID3NoHeaderError

import sqlite3

import csv

import os
import sys

walk_dir = "/media/leo/2TBVol2/High Quality Music"
sqlite_file = "musicdb.db"

cmd = ""

try:
    cmd = sys.argv[1]
except IndexError:
    print("Usage musicsync.py <syncdb|gen_playlist>")

conn = sqlite3.connect(sqlite_file)
conn.text_factory = str

c = None

tn = "songs"
fp = "file_path"
ar = "artist"
t = "title"
al = "album"
b = "bitrate"
ft = "filetype"
tbl = "songs"


query_count = 0
query_write = 150


def add_file(file_path, basic_data):
    global query_count
    album = basic_data['album']
    artist = basic_data['artist']
    title = basic_data['title']
    #file_path = (file_path)
    bitrate = basic_data['bitrate']
    filetype = basic_data['filetype']
    track_to_add = artist + " - " + title + " - " + album
    
    query_values = (file_path, artist, title, album, bitrate, filetype)

    query = "REPLACE INTO {tn} ({fp},{ar},{t},{al},{b},{ft}) \
    VALUES (?, ?, ?, ?, ?, ?)".\
    format(tn=tn, fp=fp, ar=ar, t=t, al=al, b=b, ft=ft)
    #print(query)
    c.execute(query, query_values)
    query_count += 1
    if query_count == query_write:
        query_count = 0
        conn.commit()
        print("Writing DB.. " + artist)
    #print("Adding: " + track_to_add)

def id3_to_basic(id3data, bitrate=None):
    basic_data = {
        'album': "",
        'artist': "",
        'title': "",
        'bitrate': 0,
        'filetype': 'MP3'
    }
    album = ""
    artist = ""
    title = ""
    if bitrate:
        basic_data['bitrate'] = bitrate
    try:
        album = id3data['TALB'].text[0]
    except KeyError:
        pass
    try:
        artist = id3data['TPE1'].text[0]
    except KeyError:
        pass
    try:
        title = id3data['TIT2'].text[0]
    except KeyError:
        pass
    basic_data['album'] = album
    basic_data['title'] = title
    basic_data['artist'] = artist
    return basic_data

def flac_to_basic(flacdata):
    basic_data = {
        'album': "",
        'artist': "",
        'title': "",
        'bitrate': 0,
        'filetype': 'FLAC'
    }
    album = ""
    artist = ""
    title = ""
    try:
        album = flacdata['album'][0]
    except KeyError:
        pass
    try:
        artist = flacdata['artist'][0]
    except KeyError:
        pass
    try:
        title = flacdata['title'][0]
    except KeyError:
        pass

    basic_data['album'] = album
    basic_data['artist'] = artist
    basic_data['title'] = title
    try:
        basic_data['bitrate'] = flacdata.info.bitrate / 1000
    except AttributeError:
        basic_data['bitrate'] = 0

    return basic_data

def ogg_to_basic(oggdata):
    basic_data = {
        'album': "",
        'artist': "",
        'title': "",
        'bitrate': 0,
        'filetype': 'OGG'
    }
    album = ""
    artist = ""
    title = ""
    try:
        album = oggdata['album'][0]
    except KeyError:
        pass
    try:
        artist = oggdata['artist'][0]
    except KeyError:
        pass
    try:
        title = oggdata['title'][0]
    except KeyError:
        pass

    basic_data['album'] = album
    basic_data['artist'] = artist
    basic_data['title'] = title
    try:
        basic_data['bitrate'] = oggdata.info.bitrate / 1000
    except AttributeError:
        basic_data['bitrate'] = 0

    return basic_data

def sync_db():
    global c
    c = conn.cursor()

    for root, subdirs, files in os.walk(walk_dir):

        for filename in files:
            
            file_path = os.path.join(root, filename)
            extension = os.path.splitext(filename)[1]

            if extension == ".mp3":
                try:
                    mp3data = MP3(file_path)
                except HeaderNotFoundError:
                    print("ERROR - MP3 header not found for file " + file_path)
                except ID3NoHeaderError:
                    print("ERROR - MP3 header not found for file " + file_path)
                try:
                    id3data = ID3(file_path)
                except ID3NoHeaderError:
                    print("ERROR - MP3 header not found for file " + file_path)
                bitrate = mp3data.info.bitrate / 1000
                basic_data = id3_to_basic(id3data, bitrate)
                add_file(file_path, basic_data)
            elif extension == ".ogg":
                oggdata = None
                oggdata = OggVorbis(file_path)
                basic_data = ogg_to_basic(oggdata)
                add_file(file_path, basic_data)
            elif extension == ".flac":
                flacdata = None
                flacdata = FLAC(file_path)
                basic_data = flac_to_basic(flacdata)
                add_file(file_path, basic_data)
            else:
                pass
    conn.commit()
    conn.close()

def gen_playlist(playlist_file):
    c = conn.cursor()

    with open(playlist_file, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        firstrow = True
        found_results = 0
        not_found_results = 0
        not_found_arr = []
        found_arr = []
        for row in reader:
            if firstrow:
                firstrow = False
            else:
                #print(row)
                title = row[0]
                first_title = title.split("-")[0]
                artist = row[1]
                first_artist = artist.split(",")[0]
                album = row[2]
                #print artist + " - " + title
                query = "SELECT * from {tn} WHERE {ar}=? and {t}=?".format(tn=tn, ar=ar, t=t)
                query_values = (first_artist, first_title)
                c.execute(query, query_values)

                results = c.fetchall()
                result_to_append = []
                
                if len(results) > 1:
                    found_flac = False
                    flac_result = []
                    highest_bitrate_result = []
                    highest_bitrate = 0
                    for result in results:
                        if result[5] == 'FLAC':
                            found_flac = True
                            flac_result = result
                        else:
                            if result[4] > highest_bitrate:
                                highest_bitrate = result[4]
                                highest_bitrate_result = result
                    if found_flac:
                        highest_bitrate_result = flac_result
                    result_to_append = list(highest_bitrate_result)
                    found_results += 1
                elif len(results) == 1:
                    #print("Found one result: " + artist + " - " + title)
                    found_results += 1
                    result_to_append = list(results[0])
                elif len(results) == 0:
                    #print("Track not found in library: " + artist + " - " + title)
                    not_found_arr.append([first_artist, first_title])
                    not_found_results += 1
                
                if len(results) > 0:
                    #print(str(result_to_append))
                    filetype = result_to_append[5]
                    file_path = result_to_append[0]
                    duration = 0
                    if filetype == "MP3":
                        mp3data = MP3(file_path)
                        duration = mp3data.info.length
                    elif filetype == "OGG":
                        oggdata = OggVorbis(file_path)
                        duration = oggdata.info.length
                    elif filetype == "FLAC":
                        flacdata = FLAC(file_path)
                        duration = flacdata.info.length
                    #TODO: relative path
                    file_path = file_path[len(walk_dir):]
                    found_arr.append([file_path, first_artist, first_title, duration])

        print("Found: " + str(found_results) + " not found: " + str(not_found_results))
        not_found_filename = "not found-" + playlist_file[:-4] + ".txt"
        with open(not_found_filename, 'wb') as not_found_file:
            for not_found in not_found_arr:
                not_found_file.write(not_found[0] + " - " + not_found[1])
                not_found_file.write(b'\n')

        found_m3u_playlist = playlist_file[:-4] + ".m3u"
        with open(found_m3u_playlist, 'wb') as export_playlist:
            export_playlist.write("#EXTM3U")
            for found in found_arr:
                line1 = "#EXTINF:" + str(int(found[3])) + ", " + found[1] + " - " + found[2]
                line2 = found[0]
                export_playlist.write(line1)
                export_playlist.write(b'\n')
                export_playlist.write(line2)
                export_playlist.write(b'\n')
                export_playlist.write(b'\n')



if cmd == "syncdb":
    sync_db()
elif cmd == "gen_playlist":
    playlist_file = ""
    try:
        playlist_file = sys.argv[2]
    except IndexError:
        print("Please provide a playlist file generater from Soundiiz")
    finally:
        gen_playlist(playlist_file)
else:
    print("Usage musicsync.py <syncdb|gen_playlist>")