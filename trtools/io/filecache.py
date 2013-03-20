import os
import types
import glob
import cPickle as pickle
from itertools import izip

import pandas as pd

from trtools.io.common import _filename

class FileCache(object):
    """
        Basically a replacement for the HDF5Store. It stores as flat files.
    """
    def __init__(self, cache_dir, filename_func=None, *args, **kwargs):
        self.cache_dir = cache_dir
        if filename_func:
            self.get_filename = types.MethodType(filename_func, self)

    @staticmethod
    def create_dir(dir):
        if not os.path.isdir(dir):
            os.makedirs(dir)

    def cache_dir_check(self):
        FileCache.create_dir(self.cache_dir)

    def get_filename(self, name):
        name = _filename(name)
        filename = os.path.join(self.cache_dir, name)
        return filename

    def put(self, name, obj):
        self.cache_dir_check()

        filename = self.get_filename(name)
        pd.save(obj, filename)

    def get(self, name):
        filename = self.get_filename(name)
        obj = pd.load(filename)
        obj.name = name
        return obj

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.put(key, value)

    def __contains__(self, key):
        filepath = self.get_filename(key)
        return os.path.exists(filepath)

    def __len__(self):
        return len(self.keys())

    def __repr__(self):
        output = '%s\nCache path: %s\n' % (type(self), self.cache_dir)

        if len(self) == 0:
            output += 'Empty'
        elif len(self) < 50:
            output += '\n'.join(map(str, self.keys()))
        else:
            output += '\n'.join(map(str, self.keys()[:50]))
            output += '\n{0} more items...'.format(len(self) - 50)

        return output

    def keys(self):
        dir = self.cache_dir
        keys = os.listdir(dir)
        return keys

    def remove(self, name):
        filename = self.get_filename(name)
        if os.path.exists(filename):
            os.unlink(filename)

    def __getstate__(self): return self.__dict__
    def __setstate__(self, d): self.__dict__.update(d)

class MetaFileCache(FileCache):
    """
    Like MetaFileCache but stores keys are pickled object.
    """
    def __init__(self, *args, **kwargs):
        """
        Parameters:
            leveled : bool / int
                Determines the folder hierarchy. False will create a flat hierarchy. Otherwise this value
                determines the depth. We are assuming the key is iterable which will determine the 
                level values.

        Example: 
            a key of ('HI', 1, 3) and leveled = 2 would create a file
            /cache_dir/HI/1/HI_1_3
            Assuming that HI_1_3 is the filename
        """
        super(MetaFileCache, self).__init__(*args, **kwargs)

        self.leveled = kwargs.pop('leveled', False)
        self._keys = {} # key -> filename

        self.keys_fn = self.get_filename('index', leveled=False)
        try:
            with open(self.keys_fn, 'rb') as f:
                keys = pickle.load(f)
                self._keys = keys
        except:
            pass

    def get_filename(self, key, leveled=None):
        """
            leveled is a param so we can call non-leveled on 'index' file
        """
        if leveled is None:
            leveled = self.leveled

        if not leveled:
            # normal flat FileCache
            return FileCache.get_filename(key)

        name = _filename(key)
        subdirs = leveled_key_dir(key, leveled)
        dir = os.path.join(self.cache_dir, *subdirs)
        FileCache.create_dir(dir)
        return os.path.join(dir, name)

    def save_keys(self):
        with open(self.keys_fn, 'wb') as f:
            pickle.dump(self._keys, f)

    def add_key(self, key):
        self._keys[key] = _filename(key)
        self.save_keys()

    def remove_key(self, key):
        del self._keys[key]
        self.save_keys()

    def keys(self):
        return self._keys.keys()

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.put(key, value)
        self.add_key(key)

    def __contains__(self, key):
        filepath = self.get_filename(key)
        return os.path.exists(filepath)

def leveled_key_dir(key, leveled):
    dirs = [str(dir) for dir, _ in izip(key, range(leveled))]
    return dirs

def leveled_filename(fc, name, length=1):
    """
    Creates a 2 deep file structure. Files will be stored in:
        /cache_dir/prefix/file

        The prefix is the first N letters of the name as determined by length
    Note:
        The filename function creates the subdir
    """
    name = _filename(name)
    subdir = os.path.join(fc.cache_dir, name[:length])
    # create the subdirs
    FileCache.create_dir(subdir)
    return os.path.join(subdir, name)

class LeveledFileCache(FileCache):
    def __init__(self, cache_dir, length=1, *args, **kwargs):
        self.length = length
        super(LeveledFileCache, self).__init__(cache_dir, *args, **kwargs) 

    def get_filename(self, name):
        return leveled_filename(self, name, self.length)

    def keys(self):
        pat = self.cache_dir + '/*/*'
        files = glob.glob(pat)
        return [os.path.basename(f) for f in files]
