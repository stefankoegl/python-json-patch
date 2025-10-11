import jsonpatch

a = {
    'key1': 'value1',
    'key2': 'value2',
    'key3': 'value3',
    'key4': 'value4',
    'key5': {
        'subkey1': 'subvalue1',
        'subkey2': 'subvalue2',
        'subkey3': 'subvalue3',
        'subkey4': 'subvalue4',
    },
}

b = {
    'key1': '1234',
    'key2': 'asdf',
    'key3': 'value3',
    'key4': 'value4',
    'key5': {
        'subkey1': 'subvalue1',
        'subkey2': 'subvalue2',
        'subkey3': 'subvalue3',
        'subkey5': 'subvalue5',
    },
    'key6': {
        'subkey1': 'subvalue1',
    },
}

print(jsonpatch.JsonPatch.from_diff(a, b).patch)
