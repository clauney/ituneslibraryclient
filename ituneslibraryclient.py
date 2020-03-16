import os.path
import pickle
import time
import sys
from pathlib import Path
home_dir = home = str(Path.home())          #more x-plat than os.getenv('HOME')
sys.path.append('~/code/shared/libpytunes/'.replace('~', home_dir))
from six.moves.urllib import parse as urlparse #parse 'file://' encoded paths
from libpytunes import Library
#from libpytunes import Song             # later :D
itunes_library_path = '~/Music/iTunes/iTunes Music Library.xml'.replace('~', home_dir)
library_cache_ttl = 60 * 10  # (sec) Refresh pickled file if older than this (seconds)

filter_config = {
        'non_music': {'kind': ('Internet audio stream', 'MPEG-4 audio stream', None,
                               'MPEG-4 video file', 'QuickTime movie url', 'MPEG audio stream')},
        'purchased_music': {'kind': ('AAC audio file', 'Purchased AAC audio file', 'Protected AAC audio file')},
        'mp3': {'kind': ('MPEG audio file')},
        'video': {'kind': ('MPEG audio file')},
        'local': {'track_type': ('File')},
        'non_local': {'track_type': ('URL')},
        'ignore_mp3_ver_audit': {'genre': ('Voice Memo', 'Podcast')},
        }

# INTERNAL APP SETTINGS

# 'WAV audio file', 
# 'MPEG audio file', 
# 'Protected MPEG-4 video file', 
# 'Protected AAC audio file', 
# 'AAC audio file', 
# None, 
# 'Internet audio stream', 
# 'Purchased AAC audio file', 
# 'MPEG audio stream', 
# 'MPEG-4 audio stream', 
# 'QuickTime movie url', 
# 'MPEG-4 video file'


non_music_key = 'kind'
non_music_values = (None, 'Internet audio stream', 'MPEG audio stream', 'MPEG-4 audio stream', 'MPEG-4 video file', 'QuickTime movie url')

purchased_music_key = 'kind'
purchased_music_values = ('AAC audio file', 'Purchased AAC audio file', 'Protected AAC audio file')

non_local_items_key = 'track_type'
non_local_items_values = ('URL')

mp3_version_audit_ignore_types = ('Voice Memo', 'Podcast')

class ThePickler():
    def save_to_file(filename, data):
        '''(str, obj)->None
        Writes the data supplies to a file named <filename>.pf
        '''
        pickle.dump(data, open(filename+'.pf', "wb"))
    def read_from_file(filename):
        return pickle.load(open(filename+'.pf', "rb"))

class myTunes():
    def __init__(self, itunes_lib_path, **kwargs):
        '''(str, kwargs)->None
        Kwargs supported:
            * library_cache_ttl: myTunes uses a cached copy of the itunes
              library. This value is the ttl of that cache in seconds. Defaults to
              10 minutes
            * filters: filter config which can be fed to song searches to filter results.
              Filters are specifed as a dict of kv pairs, with k=filternme and v=dict with
              one kv pair representing <field>:<list of field values the filter represents>
              e.g.:
                filters={'purchased_music': {'kind': ('AAC audio file', 'Purchased AAC audio file', 'Protected AAC audio file')}},
                filters={'non_local': {'track_type': ('URL')},
                         'play_some_skynyrd': {'artist': ('Lynyrd Skynyrd')}}
                
        '''
        self.lib_path = itunes_lib_path
        self._pf = '_itl.p'
        self._pf_exp = kwargs.get('library_cache_ttl', 600)
        self.filters = kwargs.get('filters', {})
        self._refresh_lib()
    def _refresh_lib(self):
        if not os.path.isfile(self._pf) or os.path.getmtime(self._pf) + self._pf_exp < int(time.time()):
            itl_source = Library(self.lib_path)
            pickle.dump(itl_source, open(self._pf, "wb"))
        self.lib = pickle.load(open(self._pf, "rb"))
        self.songs_by_type = {}
        self.song_type_report={}
        self.songs_by_type, self.song_type_report = self._group_songs(self.lib.songs.values(), 'kind')
        #self.itunes_base_dir = self.lib.il.get('Music Folder', '').replace('file:///', '').replace('%20', ' ')
        self.itunes_base_dir = urlparse.unquote(urlparse.urlparse(self.lib.il.get('Music Folder')).path[1:])
    def _group_songs(self, song_list, group_key):
        returndict={}
        for sv in song_list:
            group_val=sv.ToDict().get(group_key)
            if not returndict.get(group_val):
                returndict[group_val] = []
            returndict[group_val].append(sv)
        returnreport={}
        for k in returndict.keys():
            returnreport[k]=len(returndict[k])
        return returndict,returnreport
    @property
    def num_songs(self):
        return len(self.lib.songs)
    @property
    def playlists(self):
        return self.lib.getPlaylistNames()
    def diff_playlists(self, plist1_name, plist2_name):
        '''(str, str)->dict
        Returns a dict containing 2 k:v pairs, each containing a list of songs in
        that playlist that do not appear in the other playlist
        >>>diff_playlists('70s 1', '70s')
        {'only_in_{}'.format(plist1_name)}
        '''
        p1 = self.lib.getPlaylist(plist1_name).tracks
        p2 = self.lib.getPlaylist(plist2_name).tracks        
        return {'only_in_{}'.format(plist1_name): [d.name for d in p1 if d not in p2],
                'only_in_{}'.format(plist2_name): [d.name for d in p2 if d not in p1],
                }
    def tattle_songs_with_bad_info(self):
        self._refresh_lib()
        pass
    def search_songs_multi_params(self, **kwargs):
        '''(kwargs)->list
        Search songs by song parameters expressed as kwargs.
        kwargs supported: 
            * ignore_case=bool. NOT YET SUPPORTED #!!!!
            * any metadata field name in Song=str. Used as search filter. Commonly populated:
                'name', 'artist', 'album_artist', 'composer', 'album', 'genre',
                'kind', 'year', 'track_type', 'podcast', 'movie', 'loved', 'album_loved'
        >>>deej.search_songs_multi_params(artist='Boston')
        '''
        self._refresh_lib()
        returndict=self.lib.songs.copy()
        for k,v in kwargs.items():
            returndict = {songnum:songobj for songnum,songobj in returndict.items() if songobj.ToDict().get(k) and (songobj.ToDict().get(k) == v or str(songobj.ToDict().get(k)).lower()==str(v).lower())}
#            print(returndict)
#        return returndict
        return self._songlib_to_dict(returndict), len(returndict)
    def search_songs_multi_params_alt(self, **kwargs): #works as well as the above, will test for scale to see which performs better. Probably the above wins.
        self._refresh_lib()
        returndict=self.lib.songs.copy()
        for k,v in kwargs.items():
            for num,song in self.lib.songs.items():
#                if not song.ToDict().get(k) or song.ToDict().get(k).lower()!=v.lower(): #!!!! wrong behavior
                if not song.ToDict().get(k) or song.ToDict().get(k)!=v:
                    returndict.pop(num,{})                    
        return self._songlib_to_dict(returndict), len(returndict)
#        return returndict

    def _remove_none_from_dict(self, sparsedict, skiplist=[]):
        '''(dict[, list])->dict
        For the passed dictionary, returns a dict consisting of all its k:v pairs
        where k and v is not None.
        If skiplist is provided, those keys will NOT be removed from the return dict
        '''
        return {k:v for k,v in sparsedict.items() if v or k in skiplist}
    def _songlib_to_dict(self, songdict):
        '''(dict)->dict
        Returns a dict representation of the songlib, with all 'None' strings removed.
        '''
        returndict = {}
        for num, obj in songdict.items():
            if type(obj) != dict: obj = obj.ToDict()
            returndict[num] = self._remove_none_from_dict(obj)
        return returndict
    def search_songs_by_logic_expr(self, search_key, search_value, search_type, inverse=False):
        '''(str,str,str(in|equal),[bool])->list,int
        Returns a tuple of (matchlist, # of matches) for songs whose value for the field specified
        by search_key matches the search_value parameter based on logic specified in search_type:
            'in' - search_value is in song.dict[search_key] (not in for inverse=True)
            'is' - search_value equals song.dict[search_key] (not equal for inverse=True)

        >>>deej.search_songs_by_logic_expr('artist','52','in')

        >>>deej.search_songs_by_logic_expr('location', "Users/heatherkrause/Music/iTunes/iTunes Media/Music/Compilations/A Fine Romance/01 T'aint Nobody's Bizness", 'in')

        >>>deej.search_songs_by_logic_expr('location', "Users/heatherkrause/Music/iTunes/", 'in', True)

        >>>deej.search_songs_by_logic_expr('name','Illegal Immigration','in')
        ([{'name': '181: Does Illegal Immigration Help or Hurt the Economy?',
           'track_id': 69882,
           'album': 'Money For the Rest of Us',
           'genre': 'Podcast',
           'size': 30393573,
           'total_time': 1899000,
           'date_added': time.struct_time(tm_year=2018, tm_mon=8, tm_mday=1, tm_hour=3, tm_min=10, tm_sec=58, tm_wday=2, tm_yday=213, tm_isdst=-1),
           'persistent_id': '91D04FFA74536899',
           'location_escaped': 'http://rss.art19.com/episodes/9d45742e-3121-407c-a05b-af41e242e75c.mp3',
           'location': 'episodes/9d45742e-3121-407c-a05b-af41e242e75c.mp3',
           'length': 1899000,
           'track_type': 'URL',
           'podcast': True}],
         1)
        '''
#        print('search key', search_key, 'search value', search_value, 'search_type', search_type)
        self._refresh_lib()
        if search_key=='location':
            search_value = search_value.lstrip('/')
        if search_type == 'in':
#            returnlist = [self._remove_none_from_dict(v.ToDict(), [search_key]) for k,v in self.lib.songs.items() if v.ToDict().get(search_key) and (search_value.lower() in v.ToDict().get(search_key, '').lower()) != inverse]
            returnlist = [self._remove_none_from_dict(d, [search_key]) for d in self.songs if (
                    (str(search_value)).lower() in d.get(search_key, 'None').lower()
                    ) != inverse]
        elif search_type == 'is':
#            returnlist = [self._remove_none_from_dict(v.ToDict()) for k,v in self.lib.songs.items() if v.ToDict().get(search_key) and (search_value.lower() == v.ToDict().get(search_key, '').lower()) != inverse]
#            returnlist = [self._remove_none_from_dict(v.ToDict(), [search_key]) for k,v in self.lib.songs.items() if (str(search_value).lower() == str(v.ToDict().get(search_key, 'None')).lower()) != inverse]
            returnlist = [self._remove_none_from_dict(d, [search_key]) for d in self.songs if (
                    (str(search_value)).lower() == d.get(search_key, 'None').lower()
                    ) != inverse]
        return returnlist, len(returnlist)
    def audit_songs_noband(self, music_only=True):
        self._refresh_lib()
        returndict = {k:v.ToDict() for k, v in self.lib.songs.items() if v.artist==None and 
                ((not music_only) or (not v.podcast and not v.movie))}
        return self._songlib_to_dict(returndict), len(returndict)
    @property
    def songs(self):
        self._refresh_lib()
        return [self._remove_none_from_dict(v.ToDict()) for k, v in self.lib.songs.items()]
    @property
    def songs_music(self):
        self._refresh_lib()
        return [self._remove_none_from_dict(v.ToDict()) for k, v in self.lib.songs.items() if 
                v.ToDict().get(non_music_key) not in non_music_values and
                v.ToDict().get(non_local_items_key) not in non_local_items_values
                ]
    @property
    def itunes_path(self):
        '''()->str
        Returns the directory that is the root of the iTunes library
        >>>deej.itunes_path
        'Users/heatherkrause/Music/iTunes'
        '''
        return self.lib_path[1:self.lib_path.rfind('/')]
    def audit_songs_not_in_itunes_path(self, exclude_url = True):
        self._refresh_lib()
        not_in = self.search_songs_by_logic_expr('location', self.itunes_path, 'in', True)[0]
        returndict = not_in if not exclude_url else [d for d in not_in if (d[non_local_items_key] not in non_local_items_values)]
        return returndict, len(returndict)
    def audit_songs_noname(self):
        self._refresh_lib()
        returndict = {k:v.ToDict() for k, v in self.lib.songs.items() if v.name == None}
        return self._songlib_to_dict(returndict), len(returndict)
    def audit_songs_album_artist_different(self, music_only=True):
        self._refresh_lib()
        returndict = {k:v.ToDict() for k, v in self.lib.songs.items() if v.album_artist and v.artist != v.album_artist and 
                ((not music_only) or (not v.podcast and not v.movie))
                }
        return self._songlib_to_dict(returndict), len(returndict)
    def get(self, song_num, include_empty_fields=False):
        self._refresh_lib()
        returndict = self.lib.songs[song_num].ToDict()
        if not include_empty_fields:
            returndict = self._remove_none_from_dict(returndict)
        return returndict
    def print_song_basic_info(self,song):
        print('name:', song.name, 'album:', song.album, 'trackid:', song.track_id, 
              'artist:', song.artist, 'genre:', song.genre)
    @property
    def purchased_songs(self):
        return [*self.songs_by_type.get('AAC audio file', []),
                *self.songs_by_type.get('Purchased AAC audio file', []),
                *self.songs_by_type.get('Protected AAC audio file', [])]
    def audit_purchased_need_mp3(self):
        return self.audit_mp3_missing(self.purchased_songs)
    def audit_mp3_missing(self, songs_to_audit): #!!!!this ended up stupid. look @ how to break up / modularize audit_mp3_missing and audit_wav_need_mp3
        need_mp3_version = []
        have_mp3_version = []
        prob_dupes = []
        for song in songs_to_audit:
            if song.genre not in mp3_version_audit_ignore_types:
                matchlist =  [s for s in self.songs_by_type['MPEG audio file'] if s.name==song.name and s.album==song.album]
                matches = len(matchlist)
                if matches == 1:
                    have_mp3_version.append(song)
                elif matches > 1:
    #                print("ERROR! SOMETHING IS WEIRD")
                    print("NOTE! Probably a dupe (2+ MP3s with same name / album):", song.track_id)
                    prob_dupes.append(matchlist)
                elif matches == 0:
                    need_mp3_version.append(song)
#                    print("need:",song.track_id)
        print('\n{} songs with multiple / dupe mp3 versions. Songs: {}'.format(len(prob_dupes), [{d[0].name:[s.track_id for s in d]} for d in prob_dupes]))
        print('\n{} songs with mp3 version'.format(len(have_mp3_version)))
        print('\n{} songs WITHOUT mp3 version. Songs: {}'.format(len(need_mp3_version), {d.track_id:d.name for d in need_mp3_version}))
        return have_mp3_version, need_mp3_version
    def audit_wav_need_mp3(self): #!!!!this ended up stupid. look @ how to break up / modularize audit_mp3_missing and audit_wav_need_mp3
        return self.audit_mp3_missing(self.songs_by_type.get('WAV audio file'))
    def audit_dupes(self, logic='artist_album_name'):
        '''
        >>>audit_dupes() # equiv to audit_dupes('artist_album_name')
        >>>audit_dupes('artist_name')
        '''
        keys = logic.split('_')
        wd = {}
        for d in self.songs_music:
            wd.setdefault('||'.join([d.get(k, '') for k in keys]), []).append(d)
        wd = {k:v for k, v in wd.items() if len(v) > 1}
        for v in wd.values():
            for k in keys:
                print(  '{}: {} '.format(k.upper(), v[0].get(k)), end='')
            print('')
            for d in v:
                print('  {} min    {}: {}'.format(
                        round(d.get('total_time', d.get('length', 0))/60000, 1),
                        d.get('kind'),
#                        d.get('location')[d.get('location').find('Music', d.get('location').find('iTunes'))+6:]
                        d.get('location', '').replace(self.itunes_base_dir, '')
                        ))
            print('')
        return wd

#%%
#    def audit_purchased_need_mp3(self):
#        need_mp3_version=[]
#        have_mp3_version=[]
#        purchased_songs=[*self.songs_by_type['AAC audio file'],*self.songs_by_type['Purchased AAC audio file'],*self.songs_by_type['Protected AAC audio file']]
##        purchased_songs=[*self.songs_by_type['Protected AAC audio file']]
#        for song in purchased_songs:
##            matches = self.search_songs_multi_params_alt(name=song.name,album=song.album,kind="MPEG audio file")[1]
#            if song.genre != 'Voice Memo':
#                matches = len([s for s in self.songs_by_type['MPEG audio file'] if s.name==song.name and s.album==song.album])
#                if matches == 1:
#                    have_mp3_version.append(song)
#                elif matches > 1:
#    #                print("ERROR! SOMETHING IS WEIRD")
#                    print("NOTE! Probably a dupe:",song.track_id)
#                    have_mp3_version.append(song)
#                elif matches == 0:
#                    need_mp3_version.append(song)
#                    print("need:",song.track_id)
#        print('songs with mp3 version:',len(have_mp3_version))
#        print('songs WITHOUT mp3 version:',len(need_mp3_version))
#        return (have_mp3_version,need_mp3_version)

#    def audit_wav_need_mp3(self):
#        need_mp3_version=[]
#        have_mp3_version=[]
#        purchased_songs=[*self.songs_by_type['Purchased AAC audio file'],*self.songs_by_type['Protected AAC audio file']]
##        purchased_songs=[*self.songs_by_type['Protected AAC audio file']]
#        for song in purchased_songs:
#            if song.genre != 'Voice Memo':
#    #            matches = self.search_songs_multi_params_alt(name=song.name,album=song.album,kind="MPEG audio file")[1]
#                matches = len([s for s in self.songs_by_type['MPEG audio file'] if s.name==song.name and s.album==song.album])
#                if matches == 1:
#                    have_mp3_version.append(song)
#                elif matches > 1:
#    #                print("ERROR! SOMETHING IS WEIRD")
#                    print("NOTE! Probably a dupe:",song.track_id)
#                    have_mp3_version.append(song)
#                elif matches == 0:
#                    need_mp3_version.append(song)
##                    print("need:",song.track_id)
#        print('songs with mp3 version:',len(have_mp3_version))
#        print('songs WITHOUT mp3 version:',len(need_mp3_version))
#        return (have_mp3_version,need_mp3_version)

#%%
deej = myTunes(itunes_library_path, library_cache_ttl=600, filters=filter_config)
have, need = deej.audit_purchased_need_mp3()
print(deej.song_type_report)
deej.audit_dupes()


#%%

#%%


#%%
# =============================================================================
# # INITIAL AUDIT OF HK STUFF
# 
# def audit_heather_stuff():
#     deej_lib_path='/Users/heatherkrause/Music/iTunes/iTunes Music Library.xml'
#     heej = myTunes(deej_lib_path, deej_pickle_file, deej_pickle_file_expiry)
#     #hkhave,hkneed=heej.audit_purchased_need_mp3()
#     songs_maybe_convert_purchased = [*heej.songs_by_type['AAC audio file'],*heej.songs_by_type['Purchased AAC audio file'],*heej.songs_by_type['Protected AAC audio file']]
#     songs_maybe_convert_wav = [*heej.songs_by_type['WAV audio file']]
#     hkwavs_already_have, wav_to_convert = heej.audit_wav_need_mp3()
#     
#     albums_to_convert,album_convert_report=heej._group_songs(wav_to_convert,'album')
#     
#     albums_convert_all=[]
#     albums_convert_some=[]
#     albums_probs_noconvert=[]
#     album_convert_report={}
#     for alb,slist2conv in albums_to_convert.items():
#         tracks2conv=len(slist2conv)
#         mp3s_existing=len([s for s in heej.songs_by_type['MPEG audio file'] if s.album==alb])
#         maybe_convert=len([s for s in songs_maybe_convert_wav if s.album==alb])
#         album_convert_report[alb]={'wavs':maybe_convert,'mp3s':mp3s_existing,'convert':tracks2conv}
#         if tracks2conv==mp3s_existing:
#             albums_probs_noconvert.append(alb)
#         elif mp3s_existing>0:
#             albums_convert_some.append(alb)
#         else:
#             albums_convert_all.append(alb)
#     return albums_convert_all,albums_convert_some, albums_probs_noconvert, album_convert_report
# 
# albwav_conv_all, albwav_conv_some, albwav_noconv, albwav_report = audit_heather_stuff()
# 
# =============================================================================
#%%


#%%

# playlists=itl.getPlaylistNames()

# for song in itl.getPlaylist(playlists[0]).tracks:
# 	print("[{t}] {a} - {n}".format(t=song.track_number, a=song.artist, n=song.name))

# itl=init_pickled_ituneslib()

#deej.audit_songs_noname()
#deej.search_songs_multi_params(name='more than this')
#deej.search_songs_multi_params_2(name='more than this')

#for id, song in deej.lib.songs.items():
#    # if song and song.rating:
#    #     if song.rating > 80:
#            print("{n}, {r}".format(n=song.name, r=song.rating))

# =============================================================================
# crapreport = [[d.get('compilation'),d.get('album_artist'),d.get('artist'),d.get('album')] for d in deej.audit_songs_album_artist_different()[0].values()]
# bigcrap = [[
#         d.get('track_id'),
#         d.get('name'),
#         d.get('artist'),
#         d.get('album_artist'),
#         d.get('album'),
#         d.get('compilation'),
#         d.get('genre'),
#         d.get('kind'),
#         d.get('track_type'),
#         
#         ] for d in deej.audit_songs_album_artist_different()[0].values()]
# import csv
# with open('./crapreport.csv','x') as fhand:
#     for row in bigcrap:
#         csv.writer(fhand).writerow(row)
# =============================================================================


#%%

def figure_out_heather_wav_convert_stuff():
    alldupes = []
    if deej.lib.getPlaylist('todo_exact_dupes'):
        for s in deej.lib.getPlaylist('todo_exact_dupes').tracks:
            alldupes.append(deej._remove_none_from_dict(s.ToDict()))
    
    toconvert = []
    if deej.lib.getPlaylist('todo_convert_wav'):
        for s in deej.lib.getPlaylist('todo_convert_wav').tracks:
            toconvert.append(deej._remove_none_from_dict(s.ToDict()))
    #ThePickler.save_to_file('analysis/toconvert_before', toconvert)

    all_song_locs_now = [d.get('location') for d in deej.songs]
    #ThePickler.save_to_file('analysis/all_song_locs_now', all_song_locs_now)

    wav_song_locs_now = ['/'+d.get('location') for d in deej.search_songs_by_logic_expr('kind', "WAV", 'in')[0]]
    #ThePickler.save_to_file('analysis/wav_song_locs_now', wav_song_locs_now)

    alldupes_kinds = {d['kind'] for d in alldupes}
    #{'AAC audio file',
    # 'MPEG audio file',
    # 'Purchased AAC audio file',
    # 'WAV audio file'}

    '''
    >>>len([d for d in alldupes if 'WAV audio file' == d['kind']])
    1792
    >>>len([d for d in alldupes if 'AAC audio file' == d['kind']])
    53
    >>>len([d for d in alldupes if 'Purchased AAC audio file' == d['kind']])
    3
    >>>len([d for d in alldupes if 'MPEG audio file' == d['kind']])
    1864
    '''
    #%%
    wavdups = [d for d in alldupes if 'WAV audio file' == d['kind']]
    otherdups = [d for d in alldupes if 'WAV audio file' != d['kind']]
    [d['length'] for d in alldupes if d['name'] == 'Aaye Bhairav Bholanath']
    othernames = {d['name'] for d in otherdups}
    wavonlydupes = [d for d in wavdups if d['name'] not in othernames]
    wavs_to_delete = [d['name'] for d in wavonlydupes]
    #print('still to delete:', wavs_to_delete)
    #
    #
    ##%%
    #alldupes_before = ThePickler.read_from_file('alldupes_before')
    #wavdups_before = ThePickler.read_from_file('wavdups_before')
    #otherdups_before = ThePickler.read_from_file('otherdups_before')
    #
    ##%%
    #ThePickler.save_to_file('analysis/alldupes_after', alldupes)
    #ThePickler.save_to_file('analysis/wavdups_after', wavdups)
    #ThePickler.save_to_file('analysis/otherdups_after', otherdups)
    #alldupes_after = ThePickler.read_from_file('analysis/alldupes_after')
    #wavdups_after = ThePickler.read_from_file('analysis/wavdups_after')
    #otherdups_after = ThePickler.read_from_file('analysis/otherdups_after')
    #
    #
    ##%%
    #wavs_before = [d['location'] for d in wavdups_before]
    ##wavs_after = [d['location'] for d in deej.songs if 'WAV' in d['kind']]
    #wavs_after = [d['location'] for d in deej.songs if 'WAV' in d.get('kind','')]
    ##deleted = [d for d in wavs_before if d not in wavs_after]
    #deleted = [d['location'] for d in alldupes_before if d['location'] not in all_song_locs_now]
    #print('deleted:', deleted)
    ##print('WAVs in all dupes list:', len([d for d in alldupes if 'WAV' in d['kind']]))


#%%

# =============================================================================
# #  Example "kind" field values
# 'WAV audio file', 
# 'MPEG audio file', 
# 'Protected MPEG-4 video file', 
# 'Protected AAC audio file', 
# 'AAC audio file', 
# None, 
# 'Internet audio stream', 
# 'Purchased AAC audio file', 
# 'MPEG audio stream', 
# 'MPEG-4 audio stream', 
# 'QuickTime movie url', 
# 'MPEG-4 video file'
# =============================================================================

# =============================================================================
# # EXAMPLE SONG METADATA
#     {'name': 'John McLaughlin',
#      'work': None,
#      'movement_number': None,
#      'movement_count': None,
#      'movement_name': None,
#      'track_id': 4109,
#      'artist': 'Miles Davis',
#      'album_artist': None,
#      'composer': 'Miles Davis',
#      'album': 'Bitches Brew',
#      'genre': 'Jazz',
#      'kind': 'WAV audio file',
#      'size': 46917740,
#      'total_time': 265973,
#      'track_number': 2,
#      'track_count': 5,
#      'disc_number': 2,
#      'disc_count': 2,
#      'year': 1969,
#      'date_modified': time.struct_time(tm_year=2007, tm_mon=5, tm_mday=18, tm_hour=2, tm_min=18, tm_sec=16, tm_wday=4, tm_yday=138, tm_isdst=-1),
#      'date_added': time.struct_time(tm_year=2016, tm_mon=11, tm_mday=21, tm_hour=4, tm_min=6, tm_sec=32, tm_wday=0, tm_yday=326, tm_isdst=-1),
#      'bit_rate': 1411,
#      'sample_rate': 44100,
#      'comments': None,
#      'rating': None,
#      'rating_computed': False,
#      'play_count': 7,
#      'album_rating': None,
#      'album_rating_computed': False,
#      'persistent_id': 'F416FD10E4B36028',
#      'location_escaped': 'file:///Users/heatherkrause/Music/iTunes/iTunes%20Media/Music/Compilations/Bitches%20Brew/2-02%20John%20McLaughlin.wav',
#      'location': 'Users/heatherkrause/Music/iTunes/iTunes Media/Music/Compilations/Bitches Brew/2-02 John McLaughlin.wav',
#      'compilation': True,
#      'lastplayed': time.struct_time(tm_year=2012, tm_mon=3, tm_mday=1, tm_hour=20, tm_min=41, tm_sec=5, tm_wday=3, tm_yday=61, tm_isdst=-1),
#      'skip_count': None,
#      'skip_date': None,
#      'length': 265973,
#      'track_type': 'File',
#      'grouping': None,
#      'podcast': False,
#      'movie': False,
#      'has_video': False,
#      'loved': False,
#      'album_loved': False}
# =============================================================================

# =============================================================================
# # EXAMPLE LOCAL MOVIE METADATA
#     {'name': 'Winter Is Coming',
#      'track_id': 25093,
#      'genre': 'Fantasy',
#      'kind': 'MPEG-4 video file',
#      'size': 451979138,
#      'total_time': 3697186,
#      'date_modified': time.struct_time(tm_year=2018, tm_mon=3, tm_mday=3, tm_hour=20, tm_min=21, tm_sec=21, tm_wday=5, tm_yday=62, tm_isdst=-1),
#      'date_added': time.struct_time(tm_year=2018, tm_mon=2, tm_mday=26, tm_hour=6, tm_min=13, tm_sec=13, tm_wday=0, tm_yday=57, tm_isdst=-1),
#      'bit_rate': 160,
#      'play_count': 1,
#      'persistent_id': 'B0C5A81860D75BF4',
#      'location_escaped': 'file:///Users/heatherkrause/Desktop/video%20-%20do%20not%20back%20up/Game%20of%20Thrones/Season%201/GAME_OF_THRONES_S1_DISC1_ep1.m4v',
#      'location': 'Users/heatherkrause/Desktop/video - do not back up/Game of Thrones/Season 1/GAME_OF_THRONES_S1_DISC1_ep1.m4v',
#      'lastplayed': time.struct_time(tm_year=2018, tm_mon=3, tm_mday=3, tm_hour=3, tm_min=11, tm_sec=28, tm_wday=5, tm_yday=62, tm_isdst=-1),
#      'length': 3697186,
#      'track_type': 'File',
#      'has_video': True}
# =============================================================================

# =============================================================================
# persistent_id (String)
# name (String)
# artist (String)
# album_artist (String)
# composer = None (String)
# album = None (String)
# genre = None (String)
# kind = None (String)
# size = None (Integer)
# total_time = None (Integer)
# track_number = None (Integer)
# track_count = None (Integer)
# disc_number = None (Integer)
# disc_count = None (Integer)
# year = None (Integer)a
# date_modified = None (Time)
# date_added = None (Time)
# bit_rate = None (Integer)
# sample_rate = None (Integer)
# comments = None (String)
# rating = None (Integer)
# album_rating = None (Integer)
# play_count = None (Integer)
# location = None (String)
# location_escaped = None (String)
# compilation = False (Boolean)
# grouping = None (String)
# lastplayed = None (Time)
# skip_count = None (Integer)
# skip_date = None(Time)
# length = None (Integer)
# work = None (String)
# movement_name = None (String)
# movement_number = None (Integer)
# movement_count = None (Integer)
# loved = False (Boolean)
# album_loved = False (Boolean)
# =============================================================================

