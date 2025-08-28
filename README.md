python-json-patch
=================
### This project is a fork of the original work by Stefan Kögl.

Enhancements for Chat Applications
----------------------------------
This fork adds a **new `append` operation** designed for efficient text streaming in chat scenarios:

- Appends text to existing string values instead of replacing the entire string  
- Optimized notation for consecutive streaming operations (short and compact formats)  
- `make_patch()` automatically detects append cases and generates minimal patches  
- Fully backward compatible with RFC 6902  

Example:

```python
src = {"message": "Hello"}
dst = {"message": "Hello World"}
patch = jsonpatch.make_patch(src, dst)

# Generates:
[{"op": "append", "path": "/message", "value": " World"}]

# Instead of:
[{"op": "replace", "path": "/message", "value": "Hello World"}]
```
